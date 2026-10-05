import random

import pytest

from viralyst.models import Audience
from viralyst.personas import make_crowd

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
