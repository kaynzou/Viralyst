"""End-to-end: run the real command-line tool the way a user would."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).parent.parent


def run_cli(*args: str) -> str:
    result = subprocess.run([sys.executable, "run.py", *args], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_single_run_prints_a_full_report():
    output = run_cli("examples/good_demo.json", "--seed", "7")
    for section in ["Verdict:", "Rough reach:", "First impression:", "Weakest signal:", "A few of your followers:"]:
        assert section in output


def test_same_seed_prints_the_same_report():
    assert run_cli("examples/weak_demo.json", "--seed", "3") == run_cli("examples/weak_demo.json", "--seed", "3")


def test_many_runs_prints_outcome_odds():
    output = run_cli("examples/weak_demo.json", "--runs", "20", "--seed", "0")
    assert "(20 simulations)" in output
    assert "FLOP" in output and "VIRAL" in output


def test_audience_can_be_swapped(tmp_path):
    other = tmp_path / "gamers.audience.json"
    other.write_text('{"interests": ["gaming", "memes"], "min_age": 14, "max_age": 24}')
    output = run_cli("examples/good_demo.json", "--seed", "1", "--audience", str(other))
    assert "Verdict:" in output


def test_building_an_audience_needs_a_key():
    # Blank keys on purpose: .env never overrides a variable that's already set, so even with
    # your real key in backend/.env this test can't reach Claude or spend money.
    no_key = {"PATH": "/usr/bin:/bin", "ANTHROPIC_API_KEY": "", "ANTHROPIC_AUTH_TOKEN": ""}
    result = subprocess.run([sys.executable, "build_audience.py", "indie founders", "--out", "x.json"],
                            cwd=BACKEND, capture_output=True, text=True, env=no_key)
    assert result.returncode != 0
    assert "No Claude API key found" in result.stderr
