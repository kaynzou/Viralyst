import pytest

from viralyst.algorithm import BENCHMARKS, MAX_SIGNAL_BOOST, WEIGHTS, engagement_rates, score, signal_strengths
from viralyst.models import Persona, Reaction


def make_reaction(**actions) -> Reaction:
    persona = Persona("test_1", 30, ["ai"], True, 0.5, 0.5, 20)
    return Reaction(persona, **actions)


def test_weights_add_up_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_typical_reel_scores_exactly_one():
    assert score(dict(BENCHMARKS)) == pytest.approx(1.0)


def test_twice_as_good_on_every_signal_scores_two():
    assert score({s: 2 * BENCHMARKS[s] for s in BENCHMARKS}) == pytest.approx(2.0)


def test_one_huge_signal_is_capped():
    rates = {s: 0.0 for s in BENCHMARKS}
    rates["follow"] = 1.0  # 125x the benchmark
    assert signal_strengths(rates)["follow"] == MAX_SIGNAL_BOOST
    assert score(rates) == pytest.approx(WEIGHTS["follow"] * MAX_SIGNAL_BOOST)


def test_engagement_rates_count_actions():
    reactions = [
        make_reaction(watch_fraction=1.0, liked=True, shared=True),
        make_reaction(watch_fraction=0.5, liked=True),
        make_reaction(watch_fraction=0.0),
        make_reaction(watch_fraction=0.5),
    ]
    rates = engagement_rates(reactions)
    assert rates["watch"] == pytest.approx(0.5)
    assert rates["like"] == pytest.approx(0.5)
    assert rates["share"] == pytest.approx(0.25)
    assert rates["save"] == 0.0
