"""Shared helpers for talking to Claude: models, prices, cost tracking and request settings."""

import os
import threading
from dataclasses import dataclass


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


MISSING_KEY = "No Claude API key found. Copy backend/.env.example to backend/.env and paste your key into it."
BAD_KEY = "Claude rejected the API key. Check the key in backend/.env."


def has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def fallback_options(model: str) -> dict:
    """If a safety check ever declines a request, Anthropic retries it on another model.
    Returns a fresh dict every time, because the SDK adds to it while building a request."""
    if model == "claude-haiku-4-5":
        return {}  # server-side fallbacks aren't offered for Haiku 4.5
    return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


class Usage:
    """Adds up tokens and dollars across many calls, even calls running at the same time."""

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
