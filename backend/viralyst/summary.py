"""What a simulation means, as plain data. The terminal report prints it; the website draws it."""

from collections import Counter

from .algorithm import engagement_rates, signal_strengths
from .models import Reaction, WaveResult

STAGES = {
    1: "FLOP: stalled with your followers",
    2: "NICHE: reached similar people but didn't break out",
    3: "SOLID: made it to Explore, then cooled off",
    4: "STRONG: reached a broad audience before slowing down",
    5: "VIRAL: still spreading after the biggest wave",
}

TIPS = {
    "watch": "People leave early. Make the first 3 seconds show the payoff, and cut anything slow.",
    "share": "Nothing makes people send it to a friend. Add a surprising result, a relatable pain, or a 'this is so you' moment.",
    "save": "No reason to save it. Add a concrete tip, steps, or a number people will want to come back to.",
    "comment": "Few comments. End on a question or a mildly bold opinion people want to answer.",
    "like": "Low overall appeal. The idea may be unclear: say what the product does in one sentence, early.",
    "follow": "Viewers don't follow. Make it obvious what else they'll get from your account.",
}


def furthest_stage(results: list[WaveResult]) -> int:
    """1 = stalled in wave 1 ... 4 = stalled in wave 4, 5 = passed every wave."""
    return len(results) + (1 if results[-1].passed else 0)


def all_reactions(results: list[WaveResult]) -> list[Reaction]:
    return [r for wave in results for r in wave.reactions]


def reach(results: list[WaveResult]) -> int:
    return sum(wave.wave.represents for wave in results)


def scroll_rate(reactions: list[Reaction]) -> float:
    return sum(r.scrolled_past for r in reactions) / len(reactions)


def segments(reactions: list[Reaction]) -> dict[str, dict]:
    """How the target audience and everyone else engaged, separately."""
    result = {}
    for key, in_target in [("target", True), ("others", False)]:
        group = [r for r in reactions if r.persona.in_target == in_target]
        if group:
            rates = engagement_rates(group)
            result[key] = {"viewers": len(group), "watch": rates["watch"], "like": rates["like"], "share": rates["share"]}
    return result


def signals(reactions: list[Reaction]) -> dict[str, float]:
    return signal_strengths(engagement_rates(reactions))


def weakest(strengths: dict[str, float]) -> str:
    return min(strengths, key=strengths.get)


def outcome_odds(all_results: list[list[WaveResult]]) -> dict[int, float]:
    """For many runs: how often each stage was the final one."""
    counts = Counter(furthest_stage(results) for results in all_results)
    return {stage: counts[stage] / len(all_results) for stage in STAGES}
