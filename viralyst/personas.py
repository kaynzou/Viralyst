"""Generate crowds of simulated Instagram users.

Every crowd mixes people inside the target audience with people outside it,
because Instagram never shows a reel only to the "right" people.
"""

import random

from .models import Audience, Persona

# Interests found across Instagram. People outside the target audience draw from these.
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


def make_persona(rng: random.Random, audience: Audience, in_target: bool) -> Persona:
    if in_target:
        age = rng.randint(audience.min_age, audience.max_age)
        # Two interests from the target list, plus one random hobby.
        interests = rng.sample(audience.interests, k=min(2, len(audience.interests)))
        hobbies = [i for i in GENERAL_INTERESTS if i not in interests]
        interests.append(rng.choice(hobbies))
    else:
        age = rng.randint(16, 60)
        outside = [i for i in GENERAL_INTERESTS if i not in audience.interests]
        interests = rng.sample(outside, k=3)

    return Persona(
        name=f"{rng.choice(FIRST_NAMES)}_{rng.randint(10, 99)}",
        age=age,
        interests=interests,
        in_target=in_target,
        pickiness=rng.uniform(0.2, 0.9),
        share_tendency=rng.uniform(0.05, 0.6),  # most people rarely share
        attention_span=rng.randint(8, 45),
    )


def make_crowd(rng: random.Random, audience: Audience, size: int, target_fraction: float) -> list[Persona]:
    return [make_persona(rng, audience, in_target=rng.random() < target_fraction) for _ in range(size)]
