"""Generate crowds of simulated Instagram users.

Every crowd mixes people inside the target audience with people outside it,
because Instagram never shows a reel only to the "right" people.

People are made from archetypes (templates like "teen gamer" or "SaaS founder").
Each person gets small random differences, so two people from the same archetype
are similar but not identical.
"""

import random
from pathlib import Path

from .loading import load_archetypes
from .models import Archetype, Audience, Persona

# The only interest tags allowed. A fixed list keeps tags comparable: "ai" always means the same thing.
GENERAL_INTERESTS = [
    "fitness", "cooking", "travel", "fashion", "gaming", "music", "memes",
    "pets", "sports", "beauty", "parenting", "cars", "finance", "art",
    "movies", "tech", "startups", "productivity", "ai", "design", "coding",
    "marketing", "saas", "education",
]

FIRST_NAMES = [
    "aisha", "ben", "carlos", "dana", "emeka", "fatima", "george", "hana",
    "isha", "jonas", "kofi", "lena", "mateo", "nina", "omar", "priya",
    "quinn", "rahul", "sofia", "tomas", "uma", "viktor", "wei", "yara", "zoe",
]

# What people are doing while they scroll. The same person reacts differently in bed than at work.
MOMENTS = [
    "on a lunch break", "in bed, about to sleep", "on the bus to work", "procrastinating at work",
    "waiting in a queue", "on the couch after a long day", "just woke up, still in bed",
    "between classes or meetings", "bored on a weekend afternoon", "taking a break from studying",
]

# Everyday Instagram users who are NOT the target audience (hand-written, in data/everyone_else.json).
EVERYONE_ELSE = load_archetypes(Path(__file__).parent / "data" / "everyone_else.json")


def nudge(rng: random.Random, value: float, spread: float) -> float:
    """Move a 0-1 value a little in a random direction, staying between 0 and 1."""
    return min(1.0, max(0.0, value + rng.uniform(-spread, spread)))


def from_archetype(rng: random.Random, archetype: Archetype, in_target: bool, min_age: int, max_age: int) -> Persona:
    return Persona(
        name=f"{rng.choice(FIRST_NAMES)}_{rng.randint(10, 99)}",
        age=min(max_age, max(min_age, archetype.age + rng.randint(-4, 4))),
        interests=list(archetype.interests),
        in_target=in_target,
        pickiness=nudge(rng, archetype.pickiness, 0.15),
        share_tendency=nudge(rng, archetype.share_tendency, 0.1),
        attention_span=max(3, round(archetype.attention_span * rng.uniform(0.7, 1.3))),
        occupation=archetype.occupation,
        location=archetype.location,
        bio=archetype.bio,
        moment=rng.choice(MOMENTS),
    )


def make_persona(rng: random.Random, audience: Audience, in_target: bool) -> Persona:
    if in_target and audience.archetypes:
        return from_archetype(rng, rng.choice(audience.archetypes), True, audience.min_age, audience.max_age)

    if in_target:
        # No archetypes for this audience: build a simple person from its interest tags.
        interests = rng.sample(audience.interests, k=min(2, len(audience.interests)))
        hobbies = [i for i in GENERAL_INTERESTS if i not in interests]
        interests.append(rng.choice(hobbies))
        return Persona(
            name=f"{rng.choice(FIRST_NAMES)}_{rng.randint(10, 99)}",
            age=rng.randint(audience.min_age, audience.max_age),
            interests=interests,
            in_target=True,
            pickiness=rng.uniform(0.2, 0.9),
            share_tendency=rng.uniform(0.05, 0.6),  # most people rarely share
            attention_span=rng.randint(8, 45),
            moment=rng.choice(MOMENTS),
        )

    # Outsiders: anyone from the everyday pool who shares none of the audience's interests.
    outsiders = [a for a in EVERYONE_ELSE if not set(a.interests) & set(audience.interests)] or EVERYONE_ELSE
    return from_archetype(rng, rng.choice(outsiders), False, 16, 70)


def make_crowd(rng: random.Random, audience: Audience, size: int, target_fraction: float) -> list[Persona]:
    return [make_persona(rng, audience, in_target=rng.random() < target_fraction) for _ in range(size)]
