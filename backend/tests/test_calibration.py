"""Tests for benchmarks and calibration. Every number here is made up for testing:
real results only ever come from your own calibration/results.csv."""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from viralyst import api, benchmarks
from viralyst.agent import MockAgent
from viralyst.algorithm import BENCHMARKS, score
from viralyst.calibration import (CalibrationModel, Point, calibrate, fit_line, leave_one_out_miss, load_model,
                                  load_results, ranks, save_model, spearman)
from viralyst.simulation import run_cascade

BACKEND = Path(__file__).parent.parent


# ---------- Benchmarks ----------

def test_measuring_gives_every_signal_above_zero():
    rates = benchmarks.measure(MockAgent(), people=200)
    assert set(rates) == set(BENCHMARKS)
    assert all(rate > 0 for rate in rates.values())


def test_rules_benchmarks_in_the_code_are_up_to_date():
    # If personas or the rules agent change, this fails until BENCHMARKS is re-measured.
    measured = benchmarks.measure(MockAgent(), people=20_000)
    for signal in BENCHMARKS:
        assert measured[signal] == pytest.approx(BENCHMARKS[signal], rel=0.15, abs=0.002)


def test_saved_benchmarks_are_loaded_back(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmarks, "CALIBRATION_DIR", tmp_path)
    assert benchmarks.load("claude-haiku-4-5") is None
    benchmarks.save("claude-haiku-4-5", dict(BENCHMARKS), people=300)
    assert benchmarks.load("claude-haiku-4-5") == pytest.approx(BENCHMARKS)


def test_an_agent_with_its_own_benchmarks_is_scored_against_them(good_demo):
    video, audience = good_demo

    class StrictAgent(MockAgent):
        benchmarks = {signal: rate * 2 for signal, rate in BENCHMARKS.items()}  # "typical" is twice as good

    normal = run_cascade(video, audience, MockAgent(), seed=7)[0]
    strict = run_cascade(video, audience, StrictAgent(), seed=7)[0]
    assert strict.rates == normal.rates  # the same people did the same things...
    # ...but are judged against a tougher yardstick. (Not exactly half the score: the 3x cap
    # limited some signals before, so halving them changes the total less.)
    assert strict.score == pytest.approx(score(normal.rates, StrictAgent.benchmarks))
    assert strict.score < normal.score
    assert strict.benchmarks == StrictAgent.benchmarks


# ---------- The statistics ----------

def test_ranks_share_ties():
    assert ranks([10, 20, 20, 30]) == [1, 2.5, 2.5, 4]


def test_spearman_measures_order():
    assert spearman([1, 2, 3, 4], [10, 20, 35, 90]) == pytest.approx(1.0)  # same order, any spacing
    assert spearman([1, 2, 3, 4], [9, 7, 5, 1]) == pytest.approx(-1.0)
    assert spearman([1, 1, 1], [3, 5, 8]) == 0.0  # no variety, no information


def test_fit_line_finds_an_exact_line():
    xs = [1, 2, 3, 4, 5]
    intercept, slope = fit_line(xs, [0.5 + 0.3 * x for x in xs])
    assert intercept == pytest.approx(0.5) and slope == pytest.approx(0.3)
    assert fit_line([2, 2, 2], [1, 2, 3]) == (2.0, 0.0)


def make_points(stages, views, followers=1000):
    return [Point(f"video {i}", followers, v, s) for i, (s, v) in enumerate(zip(stages, views))]


def test_a_perfect_relationship_is_predicted_exactly():
    stages = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    views = [round(1000 * 10 ** (-0.5 + 0.3 * s)) for s in stages]  # made up to sit exactly on a line
    model = calibrate(make_points(stages, views), "rules")
    assert model.spearman == pytest.approx(1.0)
    assert model.slope == pytest.approx(0.3, abs=0.01)
    assert model.typical_miss == pytest.approx(1.0, abs=0.02)  # leave-one-out misses by ~nothing


def test_noise_makes_the_typical_miss_bigger():
    stages = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    views = [300, 900, 400, 3000, 1500, 9000]
    assert leave_one_out_miss(make_points(stages, views)) > 1.3


def test_too_few_videos_is_refused():
    with pytest.raises(ValueError):
        calibrate(make_points([1, 2, 3], [100, 200, 300]), "rules")


def test_expected_views_scale_with_followers():
    model = CalibrationModel(intercept=0.0, slope=0.5, videos=10, spearman=0.8, typical_miss=2.0,
                             agent="rules", fitted_on="2026-10-07")
    assert model.views_per_follower(2) == pytest.approx(10.0)  # 10 ** (0 + 0.5 * 2)
    assert model.expected_views(2, followers=500) == pytest.approx(5000)


def test_models_are_saved_and_loaded(tmp_path):
    model = CalibrationModel(0.1, 0.2, 12, 0.7, 2.1, "rules", "2026-10-07")
    save_model(model, tmp_path / "model.json")
    assert load_model(tmp_path / "model.json") == model
    assert load_model(tmp_path / "missing.json") is None


def test_results_file_skips_comments_and_rejects_zero(tmp_path):
    good = tmp_path / "results.csv"
    good.write_text("video,followers,views\n# a comment row,,\nexamples/good_demo.json,1200,3400\n\n")
    assert [(r.video, r.followers, r.views) for r in load_results(good)] == [("examples/good_demo.json", 1200, 3400)]
    bad = tmp_path / "bad.csv"
    bad.write_text("video,followers,views\nexamples/good_demo.json,1200,0\n")
    with pytest.raises(ValueError):
        load_results(bad)


def test_calibrate_command_end_to_end(tmp_path):
    rows = ["video,followers,views"]
    for weak, typical, good in [(150, 900, 6000), (220, 700, 4800)]:  # made-up test numbers
        rows += [f"examples/weak_demo.json,1000,{weak}", f"examples/typical_reel.json,1000,{typical}",
                 f"examples/good_demo.json,1000,{good}"]
    (tmp_path / "results.csv").write_text("\n".join(rows) + "\n")
    out = tmp_path / "model.json"
    result = subprocess.run([sys.executable, "calibrate.py", str(tmp_path / "results.csv"), "--runs", "30",
                             "--out", str(out)], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "Ranking check (Spearman): +0.9" in result.stdout or "Ranking check (Spearman): +1.0" in result.stdout
    assert "rough first guess" in result.stdout  # only 6 videos
    assert load_model(out).videos == 6


def test_odds_show_calibration_only_when_it_exists(monkeypatch):
    client = TestClient(api.app)
    monkeypatch.setattr(api, "load_model", lambda: None)
    assert client.get("/api/odds", params={"video": "examples/good_demo", "runs": 20}).json()["calibration"] is None

    model = CalibrationModel(0.0, 0.3, 12, 0.8, 2.0, "rules", "2026-10-07")
    monkeypatch.setattr(api, "load_model", lambda: model)
    body = client.get("/api/odds", params={"video": "examples/good_demo", "runs": 20}).json()
    assert body["calibration"]["videos"] == 12 and body["calibration"]["views_per_follower"] > 1
