"""AI personas: Claude role-plays each Instagram user deciding what to do with a reel.

Same job as MockAgent (turn a persona and a video into a Reaction), but the
decision comes from a language model instead of formulas, so personas can
explain their first impression and write real comments.
"""

import hashlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import anthropic
from pydantic import BaseModel

from .models import Persona, Reaction, VideoBrief


@dataclass
class Pricing:
    """US dollars per million tokens."""

    input: float
    output: float
    cache_read: float
    cache_write: float


# Anthropic's prices. Writing to the cache costs 1.25x normal input; reading from it is far cheaper.
PRICES = {
    "claude-opus-5-5": Pricing(input=4.00, output=20.00, cache_read=0.20, cache_write=5.00),
    "claude-sonnet-5-5": Pricing(input=2.00, output=10.00, cache_read=0.20, cache_write=2.50),
    "claude-haiku-4-5": Pricing(input=1.00, output=5.00, cache_read=0.10, cache_write=1.25),
}
DEFAULT_MODEL = "claude-opus-5-5"

# Answers already received are saved here, so re-running the same persona on the same video is free.
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "decisions"

INSTRUCTIONS = """\
You are simulating one specific person scrolling the Instagram Reels feed on their phone. You'll be told \
who they are and shown a description of the reel that just appeared on their screen. Decide what this \
person actually does, the way they really would, not the way a polite survey respondent would.

How people really behave on Reels:
- They have already scrolled past dozens of reels today and their thumb is ready to swipe. They decide \
in one or two seconds, from the opening moment alone, whether to keep watching. Most reels are swiped \
away immediately.
- Even when they keep watching, many leave before the end, especially if the video is long, slow or repetitive.
- Engagement is rare. Across the reels they actually watch, a typical person likes about 1 in 15, saves \
about 1 in 40, shares about 1 in 50, comments on about 1 in 100, and follows a new account from about 1 in 200.
- People don't care about reels outside their interests, however well made. People inside the topic are \
pickier: they notice weak claims, slow demos and things they've seen before.
- Sharing means sending it to a specific friend or posting it to their story. People do this only when \
the reel is funny, surprising, useful to someone they know, or says something about them.
- Saving means they want to come back to it later: a tip, a tool, steps, a number to remember.
- Following means they want more from this account, not just this one video.
- Comments are short and casual, written the way people really write on Instagram: lowercase, slang, \
emojis, questions, jokes, mild skepticism. Never polished, never like a marketer or a product review.
- Product demos and ads get extra suspicion. People can tell when they're being sold to, and only \
engage when the product looks genuinely useful to them.

Stay in character. You are not the creator's friend. Base every choice on this person's interests, \
personality and habits, and on what the reel actually shows.

How to answer:
- first_impression: their honest reaction in the first two seconds, in their own words, one short sentence.
- keeps_watching: false if they swipe away in the first two seconds.
- seconds_watched: how long they watch before swiping away, never more than the video's length. \
1 or 2 if they swiped away immediately.
- liked, commented, shared, saved, followed: what they did. All false if they swiped away immediately.
- comment: the exact comment they posted, or an empty string if they didn't comment.
"""


class Decision(BaseModel):
    """The exact shape of answer we ask Claude for. Field order matters: the model
    writes its first impression before it decides anything else."""

    first_impression: str
    keeps_watching: bool
    seconds_watched: int
    liked: bool
    commented: bool
    comment: str
    shared: bool
    saved: bool
    followed: bool


def describe_video(video: VideoBrief) -> str:
    return (
        "The reel that just appeared on their screen:\n"
        f"- Caption: {video.title}\n"
        f"- First 3 seconds: {video.hook}\n"
        f"- What happens: {video.description}\n"
        f"- Length: {video.length_seconds} seconds\n"
    )


def describe_persona(persona: Persona) -> str:
    """Turn the persona's numbers into words a language model can role-play.
    We never say whether they're in the target audience: the model has to work that out."""
    if persona.pickiness < 0.4:
        taste = "easygoing, enjoys most things"
    elif persona.pickiness < 0.65:
        taste = "likes good stuff, skips filler"
    else:
        taste = "hard to impress and skeptical of hype"

    if persona.share_tendency < 0.2:
        sharing = "almost never sends reels to anyone"
    elif persona.share_tendency < 0.4:
        sharing = "sometimes sends reels to close friends"
    else:
        sharing = "often sends reels to friends and group chats"

    return (
        "The person:\n"
        f"- {persona.name}, age {persona.age}\n"
        f"- Interested in: {', '.join(persona.interests)}\n"
        f"- Personality: {taste}\n"
        f"- Sharing habits: {sharing}\n"
        f"- Attention: gets restless after about {persona.attention_span} seconds\n\n"
        "What does this person do?"
    )


def model_options(model: str) -> dict:
    """Request settings that differ by model. Returns fresh dicts every time, because
    the SDK adds to them and many threads build requests at once."""
    if model == "claude-haiku-4-5":
        return {}  # Haiku 4.5 has no effort setting and only thinks when asked to
    return {
        # A scroll decision doesn't need deep thinking, and thinking tokens are billed.
        "output_config": {"effort": "low"},
        # If a safety check ever declines a request, Anthropic retries it on another model.
        "betas": ["server-side-fallback-2026-07-01"],
        "fallbacks": "default",
    }


def to_reaction(persona: Persona, video: VideoBrief, d: Decision) -> Reaction:
    """Convert Claude's answer into the same Reaction the rest of the code already understands."""
    seconds = max(0, min(d.seconds_watched, video.length_seconds))
    if not d.keeps_watching:
        # Swiped away: ignore any other actions, since they can't happen without watching.
        return Reaction(persona, watch_fraction=min(seconds, 2) / video.length_seconds,
                        scrolled_past=True, thought=d.first_impression)
    comment = d.comment.strip() if d.commented else ""
    return Reaction(
        persona,
        watch_fraction=seconds / video.length_seconds,
        liked=d.liked,
        commented=bool(comment),
        shared=d.shared,
        saved=d.saved,
        followed=d.followed,
        thought=d.first_impression,
        comment=comment,
    )


def estimate_cost(model: str, video: VideoBrief, calls: int) -> float:
    """A cautious upper estimate in dollars, assuming no caching at all."""
    p = PRICES[model]
    shared_tokens = len(INSTRUCTIONS + describe_video(video)) / 4  # about 4 characters per token
    persona_tokens = 100
    output_tokens = 150 if model == "claude-haiku-4-5" else 400  # Opus and Sonnet also think a little
    per_call = ((shared_tokens + persona_tokens) * p.input + output_tokens * p.output) / 1_000_000
    return per_call * calls


class Usage:
    """Adds up tokens and dollars across many calls running at the same time."""

    def __init__(self, pricing: Pricing):
        self.pricing = pricing
        self.lock = threading.Lock()  # stops two threads from updating the counts at once
        self.calls = self.reused = self.failures = 0
        self.input_tokens = self.output_tokens = self.cache_read = self.cache_write = 0

    def add(self, usage) -> None:
        with self.lock:
            self.calls += 1
            self.input_tokens += usage.input_tokens
            self.output_tokens += usage.output_tokens
            self.cache_read += usage.cache_read_input_tokens or 0
            self.cache_write += usage.cache_creation_input_tokens or 0

    def add_reused(self) -> None:
        with self.lock:
            self.reused += 1

    def add_failure(self) -> None:
        with self.lock:
            self.failures += 1

    @property
    def cost(self) -> float:
        p = self.pricing
        return (self.input_tokens * p.input + self.output_tokens * p.output
                + self.cache_read * p.cache_read + self.cache_write * p.cache_write) / 1_000_000

    def summary(self) -> str:
        total_in = self.input_tokens + self.cache_read + self.cache_write
        return (f"AI usage: {self.calls} calls to Claude, {self.reused} answers reused from disk, "
                f"{self.failures} failed. Tokens: {total_in:,} in ({self.cache_read:,} read from cache), "
                f"{self.output_tokens:,} out. Cost: ${self.cost:.2f}")


class LLMAgent:
    def __init__(self, model: str = DEFAULT_MODEL, workers: int = 8, cache_dir: Path | None = CACHE_DIR, client=None):
        self.model = model
        self.workers = workers  # how many personas we ask at the same time
        self.cache_dir = cache_dir
        # The SDK finds the API key in the ANTHROPIC_API_KEY environment variable,
        # and automatically retries rate limits and temporary server errors.
        self.client = client or anthropic.Anthropic(max_retries=6)
        self.usage = Usage(PRICES[model])

    def react_wave(self, crowd: list[Persona], video: VideoBrief, rng=None) -> list[Reaction]:
        print(f"  Asking {len(crowd)} AI personas...", end="", file=sys.stderr, flush=True)
        start = time.monotonic()
        # Ask one person first so Claude caches the shared instructions and video,
        # then ask everyone else in parallel. They all reuse that cache.
        first = [self.react(crowd[0], video)]
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            rest = list(pool.map(lambda persona: self.react(persona, video), crowd[1:]))
        print(f" done in {time.monotonic() - start:.0f}s", file=sys.stderr)
        return [reaction for reaction in first + rest if reaction is not None]

    def react(self, persona: Persona, video: VideoBrief, rng=None) -> Reaction | None:
        decision = self.decide(persona, video)
        return to_reaction(persona, video, decision) if decision else None

    def decide(self, persona: Persona, video: VideoBrief) -> Decision | None:
        system = INSTRUCTIONS + "\n" + describe_video(video)
        user = describe_persona(persona)

        # Same model + same prompt = same cache file. A hash turns the text into a short file name.
        key = hashlib.sha256(f"{self.model}\n{system}\n{user}".encode()).hexdigest()
        path = self.cache_dir / f"{key}.json" if self.cache_dir else None
        if path and path.exists():
            self.usage.add_reused()
            return Decision.model_validate_json(path.read_text())

        decision = self.ask_claude(system, user)
        if path and decision:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(decision.model_dump_json())
        return decision

    def ask_claude(self, system: str, user: str) -> Decision | None:
        try:
            response = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=4000,
                # cache_control marks the shared part (instructions + video) for caching.
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                output_format=Decision,  # structured output: the answer must match this shape
                **model_options(self.model),
            )
        except (anthropic.RateLimitError, anthropic.OverloadedError, anthropic.InternalServerError,
                anthropic.ServiceUnavailableError, anthropic.APIConnectionError):
            # Still failing after the SDK's automatic retries: skip this one person.
            self.usage.add_failure()
            return None

        self.usage.add(response.usage)
        if response.stop_reason != "end_turn" or response.parsed_output is None:
            self.usage.add_failure()  # e.g. declined ("refusal") or cut off ("max_tokens")
            return None
        return response.parsed_output
