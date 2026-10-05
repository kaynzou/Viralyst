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

# How a typical reel performs on each signal in our simulation, measured by
# running an "average" video past 20,000 personas. Matching these exactly scores 1.0.
BENCHMARKS = {
    "watch": 0.30,
    "share": 0.016,
    "save": 0.030,
    "comment": 0.028,
    "like": 0.10,
    "follow": 0.008,
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


def signal_strengths(rates: dict[str, float]) -> dict[str, float]:
    """Each signal compared with a typical reel: 1.0 = typical, 2.0 = twice as good."""
    return {s: min(rates[s] / BENCHMARKS[s], MAX_SIGNAL_BOOST) for s in WEIGHTS}


def score(rates: dict[str, float]) -> float:
    strengths = signal_strengths(rates)
    return sum(WEIGHTS[s] * strengths[s] for s in WEIGHTS)
