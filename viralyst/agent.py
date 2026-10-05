"""How one simulated person reacts to a video.

For now the agent's "brain" is a few hand-written rules plus dice rolls.
In Phase 2 we swap in an LLM brain. The rest of the code won't notice,
because it only ever calls `agent.react(persona, video, rng)`.
"""

import random

from .models import Persona, Reaction, VideoBrief


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def relevance(persona: Persona, video: VideoBrief) -> float:
    """0-1: how well the video's topics match what this person cares about."""
    shared_interests = set(persona.interests) & set(video.topics)
    return min(1.0, len(shared_interests) / 2)  # two matches = fully relevant


class MockAgent:
    """A rule-based stand-in for an AI persona. Fast, free, and predictable."""

    def react(self, persona: Persona, video: VideoBrief, rng: random.Random) -> Reaction:
        rel = relevance(persona, video)

        # 1. The scroll decision. Real people decide in a second or two,
        #    so only the hook and their interests matter at this point.
        stay_chance = 0.15 + 0.6 * video.hook_strength + 0.3 * rel - 0.25 * persona.pickiness
        if rng.random() > stay_chance:
            return Reaction(persona, watch_fraction=rng.uniform(0.02, 0.1))

        # 2. How much do they watch? Better and more relevant videos hold
        #    attention longer; videos longer than their attention span lose them.
        watch = 0.4 + 0.35 * video.quality + 0.25 * rel + rng.uniform(-0.15, 0.15)
        if video.length_seconds > persona.attention_span:
            watch *= (persona.attention_span / video.length_seconds) ** 0.5
        watch = clamp(watch, 0.15, 1.0)

        # 3. Did they enjoy it enough to act? Each action is a separate dice roll,
        #    and harder actions (sharing, saving) need more than easy ones (liking).
        enjoyment = watch * (0.4 + 0.6 * rel) * (1 - 0.4 * persona.pickiness)

        return Reaction(
            persona,
            watch_fraction=watch,
            liked=rng.random() < 0.05 + 0.5 * enjoyment,
            commented=rng.random() < 0.02 + 0.12 * enjoyment,
            shared=rng.random() < 0.6 * persona.share_tendency * video.shareability * enjoyment,
            saved=rng.random() < 0.4 * video.save_value * enjoyment,
            followed=rng.random() < 0.08 * enjoyment * rel,
        )
