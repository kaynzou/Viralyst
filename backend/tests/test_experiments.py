"""Tests for A/B testing: the statistics, the command and the API endpoint."""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from viralyst import api
from viralyst.agent import MockAgent
from viralyst.experiments import Arm, compare, run_arm, wilson_interval

BACKEND = Path(__file__).parent.parent


def test_wilson_interval_stays_between_0_and_1():
    low, high = wilson_interval(0, 50)
    assert low == 0.0 and 0 < high < 0.1  # zero successes still leaves a little doubt
    low, high = wilson_interval(50, 50)
    assert 0.9 < low < 1.0 and high == 1.0
    low, high = wilson_interval(25, 50)
    assert low < 0.5 < high


def test_more_runs_means_a_narrower_range():
    narrow = wilson_interval(500, 1000)
    wide = wilson_interval(5, 10)
    assert narrow[1] - narrow[0] < wide[1] - wide[0]


def test_arm_statistics():
    arm = Arm("A", "demo", [1, 1, 4, 5])  # two flops, one strong, one viral
    assert arm.breakout_rate == 0.5
    assert arm.mean_stage == pytest.approx(2.75)
    assert arm.odds == {1: 0.5, 2: 0.0, 3: 0.0, 4: 0.25, 5: 0.25}


def test_a_clear_winner_is_called():
    baseline = Arm("A", "weak", [1] * 100)
    challenger = Arm("B", "good", [5] * 60 + [1] * 40)
    result = compare(baseline, challenger)
    assert result.low > 0 and result.verdict == "B is better"


def test_a_small_difference_is_too_close_to_call():
    result = compare(Arm("A", "x", [5] * 50 + [1] * 50), Arm("B", "y", [5] * 53 + [1] * 47))
    assert result.low < 0 < result.high
    assert result.verdict.startswith("Too close to call")


def test_every_version_meets_the_same_followers(good_demo, weak_demo):
    # Same seeds for both versions -> the first wave's crowd is identical, so the test is fair.
    (good, audience), (weak, _) = good_demo, weak_demo
    a = run_arm("A", weak, audience, MockAgent(), runs=20)
    b = run_arm("B", good, audience, MockAgent(), runs=20)
    assert a.runs == b.runs == 20
    assert b.mean_stage > a.mean_stage


def test_compare_command():
    result = subprocess.run([sys.executable, "compare.py", "examples/weak_demo.json", "examples/good_demo.json",
                             "--runs", "100"], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "B vs A:" in result.stdout and "B is better" in result.stdout


def test_compare_endpoint():
    client = TestClient(api.app)
    body = client.get("/api/compare", params={"videos": ["examples/weak_demo", "examples/good_demo"], "runs": 50}).json()
    assert [arm["name"] for arm in body["arms"]] == ["A", "B"]
    assert body["comparisons"][0]["verdict"] == "B is better"
    assert client.get("/api/compare", params={"videos": ["examples/good_demo"]}).status_code == 400


def test_the_range_of_a_difference_never_passes_100_points():
    # Near 0% and 100% the simple formula overshoots (it once said "+87 to +101").
    extreme = compare(Arm("A", "weak", [1] * 50), Arm("B", "great", [5] * 49 + [1]))
    assert -1.0 <= extreme.low <= extreme.difference <= extreme.high <= 1.0
    assert extreme.verdict == "B is better"
