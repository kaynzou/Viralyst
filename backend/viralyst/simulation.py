"""The cascade: show the video to a wave, score it, maybe push to the next wave.

Each wave is bigger and has more strangers (people outside your target
audience) than the one before, like going from your followers to the Explore tab.
"""

import random

from .algorithm import PUSH_THRESHOLD, engagement_rates, score
from .models import Audience, VideoBrief, Wave, WaveResult
from .personas import make_crowd

WAVES = [
    Wave("your followers", size=30, target_fraction=0.9, represents=500),
    Wave("similar non-followers", size=60, target_fraction=0.6, represents=5_000),
    Wave("Explore and Reels tab", size=120, target_fraction=0.35, represents=50_000),
    Wave("broad Reels audience", size=240, target_fraction=0.15, represents=500_000),
]


def run_cascade(video: VideoBrief, audience: Audience, agent, seed: int | None = None) -> list[WaveResult]:
    # One random generator, created from a seed, drives every dice roll.
    # Same seed -> same personas and same reactions -> same result.
    rng = random.Random(seed)
    results = []

    for number, wave in enumerate(WAVES, start=1):
        crowd = make_crowd(rng, audience, wave.size, wave.target_fraction)
        reactions = agent.react_wave(crowd, video, rng)
        if not reactions:
            raise RuntimeError(f"No persona in wave {number} produced a reaction, so the wave can't be scored.")
        rates = engagement_rates(reactions)
        result = WaveResult(number, wave, reactions, rates, score(rates), PUSH_THRESHOLD)
        results.append(result)

        if not result.passed:
            break  # the algorithm stops showing the video to new people

    return results


def furthest_stage(results: list[WaveResult]) -> int:
    """1 = stalled in wave 1 ... 4 = stalled in wave 4, 5 = passed every wave."""
    return len(results) + (1 if results[-1].passed else 0)
