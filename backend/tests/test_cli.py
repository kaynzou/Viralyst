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
