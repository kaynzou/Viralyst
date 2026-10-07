"""Our simplified version of how Instagram decides to spread a reel.

Instagram tests a new reel on a small audience, measures how people respond,
and shows it to a bigger audience only if it beats a typical reel.
We copy that loop: show it to a wave, score the wave, push further or stop.
"""

from .models import Reaction

# How much each signal counts. Instagram has said watch time and sends
# (shares) are the strongest signals for reaching people who don't follow you.
WEIGHTS = {
    "watch": 0.30,
    "share": 0.25,
    "save": 0.15,
    "comment": 0.10,
    "like": 0.10,
    "follow": 0.10,
}

# How a typical reel performs on each signal with the rule-based personas: examples/typical_reel.json
# shown to 20,000 personas (60% in the target audience). Matching these exactly scores 1.0.
# Re-measure with `uv run measure_benchmarks.py --agent rules` whenever personas or the agent change.
BENCHMARKS = {
    "watch": 0.236,
    "share": 0.014,
    "save": 0.021,
    "comment": 0.021,
    "like": 0.072,
    "follow": 0.005,
}

# A wave must beat a typical reel to earn the next, bigger audience.
PUSH_THRESHOLD = 1.0

# No single signal can count for more than 3x its benchmark, so one lucky
# share in a small wave can't carry an otherwise weak video.
MAX_SIGNAL_BOOST = 3.0


def engagement_rates(reactions: list[Reaction]) -> dict[str, float]:
    n = len(reactions)
    return {
        "watch": sum(r.watch_fraction for r in reactions) / n,
        "share": sum(r.shared for r in reactions) / n,
        "save": sum(r.saved for r in reactions) / n,
        "comment": sum(r.commented for r in reactions) / n,
        "like": sum(r.liked for r in reactions) / n,
        "follow": sum(r.followed for r in reactions) / n,
    }


def signal_strengths(rates: dict[str, float], benchmarks: dict[str, float] | None = None) -> dict[str, float]:
    """Each signal compared with a typical reel: 1.0 = typical, 2.0 = twice as good."""
    typical = benchmarks or BENCHMARKS  # AI personas can bring their own measured "typical reel"
    return {s: min(rates[s] / typical[s], MAX_SIGNAL_BOOST) for s in WEIGHTS}


def score(rates: dict[str, float], benchmarks: dict[str, float] | None = None) -> float:
    strengths = signal_strengths(rates, benchmarks)
    return sum(WEIGHTS[s] * strengths[s] for s in WEIGHTS)
