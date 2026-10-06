import random

import pytest

from viralyst.models import Audience
from viralyst.personas import GENERAL_INTERESTS, make_crowd

AUDIENCE = Audience(["productivity", "ai", "startups"], min_age=22, max_age=35)


def test_same_seed_gives_same_crowd():
    first = make_crowd(random.Random(42), AUDIENCE, 50, 0.5)
    second = make_crowd(random.Random(42), AUDIENCE, 50, 0.5)
    assert first == second


def test_target_personas_match_the_audience():
    crowd = make_crowd(random.Random(1), AUDIENCE, 200, target_fraction=1.0)
    for persona in crowd:
        assert persona.in_target
        assert AUDIENCE.min_age <= persona.age <= AUDIENCE.max_age
        assert len(set(persona.interests) & set(AUDIENCE.interests)) >= 2


def test_outsiders_share_no_target_interests():
    crowd = make_crowd(random.Random(1), AUDIENCE, 200, target_fraction=0.0)
    for persona in crowd:
        assert not persona.in_target
        assert not set(persona.interests) & set(AUDIENCE.interests)


def test_target_fraction_is_respected_on_average():
    crowd = make_crowd(random.Random(7), AUDIENCE, 5000, target_fraction=0.35)
    share_in_target = sum(p.in_target for p in crowd) / len(crowd)
    assert share_in_target == pytest.approx(0.35, abs=0.03)


def test_archetype_people_come_from_the_audience(good_demo):
    _, audience = good_demo  # has hand-written archetypes
    labels = {a.bio for a in audience.archetypes}
    crowd = make_crowd(random.Random(3), audience, 200, target_fraction=1.0)
    for persona in crowd:
        assert persona.bio in labels
        assert audience.min_age <= persona.age <= audience.max_age
        assert set(persona.interests) & set(audience.interests)
        assert 0 <= persona.pickiness <= 1 and persona.attention_span >= 3


def test_everyone_gets_a_moment_and_outsiders_get_a_life(good_demo):
    _, audience = good_demo
    for persona in make_crowd(random.Random(4), audience, 200, target_fraction=0.5):
        assert persona.moment
        if not persona.in_target:
            assert persona.occupation and persona.bio


def test_people_from_one_archetype_differ_a_little(good_demo):
    _, audience = good_demo
    crowd = make_crowd(random.Random(5), audience, 300, target_fraction=1.0)
    founders = [p for p in crowd if p.bio == audience.archetypes[0].bio]
    assert len({round(p.pickiness, 3) for p in founders}) > 1


def test_a_very_broad_audience_still_gets_outsiders():
    everything = Audience(list(GENERAL_INTERESTS), min_age=16, max_age=70)
    assert len(make_crowd(random.Random(8), everything, 50, target_fraction=0.0)) == 50
