"""Measure how a typical reel performs with a given kind of persona, so scores stay fair.

The algorithm scores a wave against a "typical reel" (algorithm.BENCHMARKS). Those numbers
were measured with the rule-based personas. AI personas might like, share or comment more or
less often, so they get their own measurement. It's saved in calibration/benchmarks.<model>.json
and LLMAgent picks it up automatically.
"""

import json
import random
from datetime import date
from pathlib import Path

from .algorithm import engagement_rates
from .loading import load_example
from .personas import make_crowd

BACKEND = Path(__file__).resolve().parent.parent
CALIBRATION_DIR = BACKEND / "calibration"
TYPICAL_REEL = BACKEND / "examples" / "typical_reel.json"
TARGET_FRACTION = 0.6  # the same audience mix the original benchmarks were measured on


def benchmark_path(model: str) -> Path:
    return CALIBRATION_DIR / f"benchmarks.{model}.json"


def measure(agent, people: int = 300, seed: int = 0) -> dict[str, float]:
    """Show the typical reel to `people` personas and return their engagement rates."""
    video, audience = load_example(TYPICAL_REEL)
    rng = random.Random(seed)
    reactions = agent.react_wave(make_crowd(rng, audience, people, TARGET_FRACTION), video, rng)
    rates = engagement_rates(reactions)
    # Scores divide by these numbers, so never let one be exactly zero.
    return {signal: max(rate, 0.001) for signal, rate in rates.items()}


def save(model: str, rates: dict[str, float], people: int) -> Path:
    path = benchmark_path(model)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"model": model, "measured_on": date.today().isoformat(), "people": people,
            "rates": {signal: round(rate, 4) for signal, rate in rates.items()}}
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def load(model: str) -> dict[str, float] | None:
    """The measured benchmarks for this model, or None if they haven't been measured yet."""
    path = benchmark_path(model)
    return json.loads(path.read_text())["rates"] if path.exists() else None
