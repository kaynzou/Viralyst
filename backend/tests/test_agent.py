import random
from dataclasses import replace

from viralyst.agent import MockAgent, relevance
from viralyst.models import Persona
from viralyst.personas import make_crowd


def test_relevance(good_demo):
    video, _ = good_demo  # topics: productivity, ai
    fan = Persona("fan_1", 30, ["productivity", "ai", "travel"], True, 0.5, 0.5, 20)
    half = Persona("half_1", 30, ["ai", "cooking", "travel"], True, 0.5, 0.5, 20)
    stranger = Persona("stranger_1", 30, ["cars", "pets", "music"], False, 0.5, 0.5, 20)
    assert relevance(fan, video) == 1.0
    assert relevance(half, video) == 0.5
    assert relevance(stranger, video) == 0.0


def test_reactions_are_valid(good_demo):
    video, audience = good_demo
    rng = random.Random(3)
    for persona in make_crowd(rng, audience, 500, 0.5):
        reaction = MockAgent().react(persona, video, rng)
        assert 0.0 <= reaction.watch_fraction <= 1.0
        if reaction.scrolled_past:
            # People who scroll past can't like, share or do anything else.
            assert not any([reaction.liked, reaction.commented, reaction.shared, reaction.saved, reaction.followed])


def scroll_rate(video, audience) -> float:
    rng = random.Random(5)
    crowd = make_crowd(rng, audience, 2000, 0.5)
    return sum(MockAgent().react(p, video, rng).scrolled_past for p in crowd) / len(crowd)


def test_stronger_hook_means_fewer_people_scroll_past(weak_demo):
    video, audience = weak_demo
    better_hook = replace(video, hook_strength=0.9)
    assert scroll_rate(better_hook, audience) < scroll_rate(video, audience) - 0.2
