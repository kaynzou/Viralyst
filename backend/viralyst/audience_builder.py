"""Turn a plain-English description of a target audience into persona archetypes, using Claude.

This runs once per audience (not once per viewer), so it uses the strongest model at
normal effort. The result is saved to a JSON file and reused for every simulation.
"""

from pydantic import BaseModel

from .agent import clamp
from .claude import DEFAULT_MODEL, PRICES, Usage, fallback_options
from .models import Archetype, Audience
from .personas import GENERAL_INTERESTS

PROMPT = """\
A founder wants to test a product demo video on simulated Instagram users before posting it. \
Below is their description of who the video is for. Turn it into {count} realistic, clearly different \
people who belong to that audience, plus a few tags that describe the audience as a whole.

Rules:
- Use only these interest tags, spelled exactly like this: {tags}
- interests (for the whole audience): the 2 to 4 tags that best describe it.
- min_age and max_age: the audience's age range.
- archetypes: {count} people. Each gets exactly 3 interest tags, including at least one of the audience's tags.
- Make them genuinely different: spread their ages across the range, use different countries and jobs, \
and include skeptics and busy or distracted people as well as fans. Real audiences are mixed.
- label: a short name for the type of person, like "bootstrapped SaaS founder".
- occupation and location: specific and realistic (a city and a country).
- bio: one or two sentences about their life and how they use Instagram. Don't use he/she pronouns.
- pickiness: 0 (easy to please) to 1 (very hard to impress).
- share_tendency: 0 (never sends reels to anyone) to 1 (sends reels constantly). Most people are below 0.5.
- attention_span: seconds before they get restless, usually between 5 and 45.

The founder's description of the audience:
{description}
"""


class ArchetypeSpec(BaseModel):
    label: str
    age: int
    occupation: str
    location: str
    interests: list[str]
    bio: str
    pickiness: float
    share_tendency: float
    attention_span: int


class AudienceSpec(BaseModel):
    interests: list[str]
    min_age: int
    max_age: int
    archetypes: list[ArchetypeSpec]


def clean(spec: AudienceSpec, description: str) -> Audience:
    """Never trust a model's output blindly: keep only known tags and keep every number in range."""
    tags = [t for t in spec.interests if t in GENERAL_INTERESTS]
    if not tags:
        raise ValueError("Claude didn't choose any known interest tags for this audience.")
    min_age = max(13, min(spec.min_age, spec.max_age))
    max_age = min(80, max(spec.min_age, spec.max_age))

    archetypes = []
    for a in spec.archetypes:
        interests = [t for t in a.interests if t in GENERAL_INTERESTS]
        if not set(interests) & set(tags):
            interests.insert(0, tags[0])  # everyone in the audience shares at least one of its interests
        archetypes.append(Archetype(
            label=a.label,
            age=int(clamp(a.age, min_age, max_age)),
            occupation=a.occupation,
            location=a.location,
            interests=interests[:3],
            bio=a.bio,
            pickiness=clamp(a.pickiness, 0.0, 1.0),
            share_tendency=clamp(a.share_tendency, 0.0, 1.0),
            attention_span=int(clamp(a.attention_span, 3, 60)),
        ))
    if not archetypes:
        raise ValueError("Claude didn't create any people for this audience.")
    return Audience(interests=tags, min_age=min_age, max_age=max_age, description=description, archetypes=archetypes)


def estimate_build_cost(model: str, count: int) -> float:
    """A cautious estimate in dollars: about 700 tokens in, 150 out per person, plus some thinking."""
    p = PRICES[model]
    return (700 * p.input + (count * 150 + 2000) * p.output) / 1_000_000


def build_audience(description: str, client, model: str = DEFAULT_MODEL, count: int = 12) -> tuple[Audience, Usage]:
    usage = Usage(PRICES[model])
    prompt = PROMPT.format(count=count, tags=", ".join(GENERAL_INTERESTS), description=description)
    response = client.beta.messages.parse(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
        output_format=AudienceSpec,
        **fallback_options(model),
    )
    usage.add(response.usage)
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise RuntimeError(f"Claude didn't return an audience (stop reason: {response.stop_reason}).")
    return clean(response.parsed_output, description), usage
