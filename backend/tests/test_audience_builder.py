"""Tests for turning a plain-English audience description into archetypes, with a fake Claude."""

from types import SimpleNamespace

import pytest

from viralyst.audience_builder import ArchetypeSpec, AudienceSpec, build_audience, clean, estimate_build_cost

FOUNDER = ArchetypeSpec(label="SaaS founder", age=30, occupation="founder", location="Austin, USA",
                        interests=["startups", "saas", "productivity"], bio="Builds in public.",
                        pickiness=0.7, share_tendency=0.3, attention_span=20)


class FakeClaude:
    def __init__(self, spec: AudienceSpec):
        self.spec, self.requests = spec, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **request):
        self.requests.append(request)
        usage = SimpleNamespace(input_tokens=700, output_tokens=2000, cache_read_input_tokens=0, cache_creation_input_tokens=0)
        return SimpleNamespace(usage=usage, stop_reason="end_turn", parsed_output=self.spec)


def test_builds_an_audience_from_a_description():
    spec = AudienceSpec(interests=["startups", "ai"], min_age=22, max_age=35, archetypes=[FOUNDER])
    claude = FakeClaude(spec)
    audience, usage = build_audience("indie founders", claude, count=1)

    assert audience.description == "indie founders"
    assert audience.interests == ["startups", "ai"]
    assert audience.archetypes[0].label == "SaaS founder"
    assert "indie founders" in claude.requests[0]["messages"][0]["content"]
    assert usage.cost > 0


def test_unknown_tags_are_dropped():
    spec = AudienceSpec(interests=["startups", "underwater basket weaving"], min_age=22, max_age=35, archetypes=[FOUNDER])
    assert clean(spec, "").interests == ["startups"]


def test_numbers_are_kept_in_range():
    wild = FOUNDER.model_copy(update={"age": 99, "pickiness": 7.0, "share_tendency": -2.0, "attention_span": 900})
    spec = AudienceSpec(interests=["startups"], min_age=35, max_age=22, archetypes=[wild])  # ages swapped too
    audience = clean(spec, "")
    person = audience.archetypes[0]
    assert (audience.min_age, audience.max_age) == (22, 35)
    assert person.age == 35
    assert person.pickiness == 1.0 and person.share_tendency == 0.0
    assert person.attention_span == 60


def test_every_archetype_shares_an_audience_interest():
    off_topic = FOUNDER.model_copy(update={"interests": ["cooking", "pets", "travel"]})
    spec = AudienceSpec(interests=["startups", "ai"], min_age=22, max_age=35, archetypes=[off_topic])
    assert "startups" in clean(spec, "").archetypes[0].interests


def test_no_valid_tags_is_an_error():
    spec = AudienceSpec(interests=["nonsense"], min_age=22, max_age=35, archetypes=[FOUNDER])
    with pytest.raises(ValueError):
        clean(spec, "")


def test_building_an_audience_is_cheap():
    assert 0 < estimate_build_cost("claude-opus-5-5", 12) < 0.25
