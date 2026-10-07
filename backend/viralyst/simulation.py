"""The cascade: show the video to a wave, score it, maybe push to the next wave.

Each wave is bigger and has more strangers (people outside your target
audience) than the one before, like going from your followers to the Explore tab.
"""

import random
from collections.abc import Iterator

from .algorithm import PUSH_THRESHOLD, engagement_rates, score
from .models import Audience, VideoBrief, Wave, WaveResult
from .personas import make_crowd

WAVES = [
    Wave("your followers", size=30, target_fraction=0.9, represents=500),
    Wave("similar non-followers", size=60, target_fraction=0.6, represents=5_000),
    Wave("Explore and Reels tab", size=120, target_fraction=0.35, represents=50_000),
    Wave("broad Reels audience", size=240, target_fraction=0.15, represents=500_000),
]


def simulate(video: VideoBrief, audience: Audience, agent, seed: int | None = None) -> Iterator[WaveResult]:
    """Run the cascade, handing back each wave the moment it's finished.

    `yield` makes this a generator: whoever loops over it gets wave 1 while wave 2
    hasn't even started. The website uses this to show waves live.
    """
    # One random generator, created from a seed, drives every dice roll.
    # Same seed -> same personas and same reactions -> same result.
    rng = random.Random(seed)
    benchmarks = getattr(agent, "benchmarks", None)  # only AI personas with measured benchmarks have these

    for number, wave in enumerate(WAVES, start=1):
        crowd = make_crowd(rng, audience, wave.size, wave.target_fraction)
        reactions = agent.react_wave(crowd, video, rng)
        if not reactions:
            raise RuntimeError(f"No persona in wave {number} produced a reaction, so the wave can't be scored.")
        rates = engagement_rates(reactions)
        result = WaveResult(number, wave, reactions, rates, score(rates, benchmarks), PUSH_THRESHOLD, benchmarks)
        yield result

        if not result.passed:
            return  # the algorithm stops showing the video to new people


def run_cascade(video: VideoBrief, audience: Audience, agent, seed: int | None = None) -> list[WaveResult]:
    """Run the whole cascade and return every wave at once."""
    return list(simulate(video, audience, agent, seed))

