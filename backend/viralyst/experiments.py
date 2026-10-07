"""A/B tests: run several versions of a video past the same simulated audience and compare them.

One run is noisy, so each version is simulated many times. The result isn't just
"B scored higher" but "B breaks out in 64% of runs (95% range 57-70%)", plus whether
the difference is big enough to trust.
"""

import math
from dataclasses import dataclass

from .models import Audience, VideoBrief
from .simulation import run_cascade
from .summary import STAGES, furthest_stage

BREAKOUT_STAGE = 4  # STRONG or VIRAL: the video reached the broad Reels audience
Z_95 = 1.96  # how many standard errors give a 95% range


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """A 95% range for a rate measured over n runs. Wilson's formula stays sensible near 0% and 100%,
    where the simple "rate ± 1.96 × standard error" would give impossible values like -3%."""
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


@dataclass
class Arm:
    """One version of the video in the test, with the final stage (1-5) of every run."""

    name: str
    title: str
    stages: list[int]

    @property
    def runs(self) -> int:
        return len(self.stages)

    @property
    def breakouts(self) -> int:
        return sum(stage >= BREAKOUT_STAGE for stage in self.stages)

    @property
    def breakout_rate(self) -> float:
        return self.breakouts / self.runs

    @property
    def breakout_range(self) -> tuple[float, float]:
        return wilson_interval(self.breakouts, self.runs)

    @property
    def mean_stage(self) -> float:
        return sum(self.stages) / self.runs

    @property
    def odds(self) -> dict[int, float]:
        return {stage: self.stages.count(stage) / self.runs for stage in STAGES}


@dataclass
class Comparison:
    """How much more (or less) often the challenger breaks out than the baseline."""

    baseline: Arm
    challenger: Arm
    difference: float  # challenger's breakout rate minus the baseline's
    low: float  # the 95% range of that difference
    high: float

    @property
    def verdict(self) -> str:
        if self.low > 0:
            return f"{self.challenger.name} is better"
        if self.high < 0:
            return f"{self.baseline.name} is better"
        return "Too close to call: the difference could be luck, so run more simulations"


def run_arm(name: str, video: VideoBrief, audience: Audience, agent, runs: int, seed: int = 0) -> Arm:
    # Every version uses the same seeds, so each one starts with exactly the same followers: a fair test.
    stages = [furthest_stage(run_cascade(video, audience, agent, seed + i)) for i in range(runs)]
    return Arm(name, video.title, stages)


def compare(baseline: Arm, challenger: Arm) -> Comparison:
    """The difference in breakout rate, with a 95% range built from both versions' Wilson ranges
    (Newcombe's method). The simpler "difference ± 1.96 × standard error" can claim impossible
    ranges like "+87 to +101 points" when rates are near 0% or 100%; this one can't."""
    p1, p2 = baseline.breakout_rate, challenger.breakout_rate
    low1, high1 = baseline.breakout_range
    low2, high2 = challenger.breakout_range
    difference = p2 - p1
    low = difference - math.sqrt((p2 - low2) ** 2 + (high1 - p1) ** 2)
    high = difference + math.sqrt((high2 - p2) ** 2 + (p1 - low1) ** 2)
    return Comparison(baseline, challenger, difference, low, high)
