"""Tests for the AI personas. They use a fake Claude, so they're free and need no API key."""

import random
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from viralyst.llm_agent import Decision, LLMAgent, describe_persona, estimate_cost, model_options
from viralyst.personas import make_crowd
from viralyst.simulation import run_cascade
from viralyst.summary import furthest_stage

LOVED_IT = Decision(first_impression="wait what, 4000 emails??", keeps_watching=True, seconds_watched=14,
                    liked=True, commented=True, comment="  need this for my inbox  ", shared=True, saved=True, followed=False)


class FakeClaude:
    """Stands in for anthropic.Anthropic(): records every request and returns a canned answer."""

    def __init__(self, decision=LOVED_IT, stop_reason="end_turn", error=None):
        self.requests = []
        self.decision, self.stop_reason, self.error = decision, stop_reason, error
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **request):
        self.requests.append(request)
        if self.error:
            raise self.error
        usage = SimpleNamespace(input_tokens=100, output_tokens=50, cache_read_input_tokens=700, cache_creation_input_tokens=0)
        parsed = self.decision if self.stop_reason == "end_turn" else None
        return SimpleNamespace(usage=usage, stop_reason=self.stop_reason, parsed_output=parsed)


@pytest.fixture
def persona(good_demo):
    _, audience = good_demo
    return make_crowd(random.Random(1), audience, 1, target_fraction=1.0)[0]


def agent_with(client, **kwargs) -> LLMAgent:
    return LLMAgent("claude-opus-5-5", client=client, cache_dir=None, **kwargs)


def test_answer_becomes_a_reaction(good_demo, persona):
    video, _ = good_demo  # 28 seconds long
    reaction = agent_with(FakeClaude()).react(persona, video)
    assert reaction.watch_fraction == pytest.approx(14 / 28)
    assert not reaction.scrolled_past
    assert reaction.liked and reaction.shared and reaction.saved and not reaction.followed
    assert reaction.comment == "need this for my inbox"  # extra spaces trimmed
    assert reaction.thought == "wait what, 4000 emails??"


def test_swiping_away_cancels_every_other_action(good_demo, persona):
    video, _ = good_demo
    contradiction = LOVED_IT.model_copy(update={"keeps_watching": False, "seconds_watched": 1})
    reaction = agent_with(FakeClaude(contradiction)).react(persona, video)
    assert reaction.scrolled_past
    assert not any([reaction.liked, reaction.commented, reaction.shared, reaction.saved, reaction.followed])


def test_watch_time_stays_within_the_video(good_demo, persona):
    video, _ = good_demo
    too_long = LOVED_IT.model_copy(update={"seconds_watched": 999})
    assert agent_with(FakeClaude(too_long)).react(persona, video).watch_fraction == 1.0


def test_empty_comment_does_not_count(good_demo, persona):
    video, _ = good_demo
    blank = LOVED_IT.model_copy(update={"comment": "   "})
    reaction = agent_with(FakeClaude(blank)).react(persona, video)
    assert not reaction.commented and reaction.comment == ""


def test_request_contents(good_demo, persona):
    video, _ = good_demo
    claude = FakeClaude()
    agent_with(claude).react(persona, video)
    request = claude.requests[0]
    system, user = request["system"][0], request["messages"][0]["content"]

    assert request["model"] == "claude-opus-5-5"
    assert request["output_format"] is Decision
    assert video.hook in system["text"] and persona.name in user
    assert system["cache_control"] == {"type": "ephemeral"}  # the shared part gets cached
    assert "target" not in user.lower()  # the persona must not be told it's in the target audience


def test_model_specific_options():
    assert model_options("claude-opus-5-5")["output_config"] == {"effort": "low"}
    assert model_options("claude-opus-5-5")["fallbacks"] == "default"
    assert model_options("claude-haiku-4-5") == {}
    # Fresh dicts each time, so parallel requests can't change each other's settings.
    assert model_options("claude-opus-5-5")["output_config"] is not model_options("claude-opus-5-5")["output_config"]


def test_a_wave_asks_everyone_and_adds_up_the_cost(good_demo):
    video, audience = good_demo
    crowd = make_crowd(random.Random(2), audience, 20, 0.5)
    agent = agent_with(FakeClaude())
    reactions = agent.react_wave(crowd, video)
    assert len(reactions) == 20
    assert agent.usage.calls == 20
    # Opus 5.5: 100 input tokens at $4, 50 output at $20, 700 cache reads at $0.20 (per million)
    assert agent.usage.cost == pytest.approx(20 * (100 * 4 + 50 * 20 + 700 * 0.20) / 1_000_000)


def test_a_declined_request_skips_that_person(good_demo, persona):
    video, _ = good_demo
    agent = agent_with(FakeClaude(stop_reason="refusal"))
    assert agent.react(persona, video) is None
    assert agent.usage.failures == 1


def test_a_rate_limit_skips_that_person(good_demo, persona):
    video, _ = good_demo
    response = httpx2.Response(429, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    agent = agent_with(FakeClaude(error=anthropic.RateLimitError("slow down", response=response, body=None)))
    assert agent.react(persona, video) is None
    assert agent.usage.failures == 1


def test_saved_answers_are_reused_for_free(good_demo, persona, tmp_path):
    video, _ = good_demo
    claude = FakeClaude()
    agent = LLMAgent("claude-opus-5-5", client=claude, cache_dir=tmp_path)
    first = agent.react(persona, video)
    second = agent.react(persona, video)
    assert len(claude.requests) == 1  # the second answer came from disk
    assert agent.usage.reused == 1
    assert first == second


def test_ai_agent_plugs_into_the_simulation(good_demo):
    video, audience = good_demo
    results = run_cascade(video, audience, agent_with(FakeClaude()), seed=1)
    # Everyone loving it should push the video through every wave.
    assert furthest_stage(results) == 5


def test_cheaper_models_cost_less(good_demo):
    video, _ = good_demo
    costs = [estimate_cost(model, video, 450) for model in ["claude-haiku-4-5", "claude-sonnet-5-5", "claude-opus-5-5"]]
    assert 0 < costs[0] < costs[1] < costs[2]


def test_rich_personas_are_described_to_claude(good_demo):
    _, audience = good_demo
    person = make_crowd(random.Random(6), audience, 1, target_fraction=1.0)[0]
    text = describe_persona(person)
    assert person.bio in text and person.occupation in text and person.moment in text
