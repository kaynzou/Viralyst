"""Settings for running online, read from environment variables.

The same code runs on your laptop and on a server. Only these variables change, and none
of them are set on your laptop, so locally everything stays open and uncapped.

    VIRALYST_ALLOWED_ORIGINS   websites that may call this API, comma-separated
                               (e.g. https://viralyst.vercel.app). localhost:3000 is always allowed.
    VIRALYST_ACCESS_CODE       if set, AI features need this code (sent in the X-Viralyst-Code header)
    VIRALYST_DAILY_BUDGET      if set, the most AI may cost per day, in US dollars (e.g. 3)
"""

import hmac
import os
import threading
from datetime import datetime, timezone

LOCAL_WEBSITE = "http://localhost:3000"
CODE_HEADER = "X-Viralyst-Code"


def allowed_origins() -> list[str]:
    extra = [o.strip().rstrip("/") for o in os.environ.get("VIRALYST_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    return [LOCAL_WEBSITE, *extra]


def access_code_required() -> bool:
    return bool(os.environ.get("VIRALYST_ACCESS_CODE"))


def code_is_valid(code: str | None) -> bool:
    """True if no code is configured (local use), or if `code` matches it.

    hmac.compare_digest takes the same time whether the first letter or the last one is wrong.
    A normal == stops at the first difference, which an attacker could time to guess the code
    one letter at a time."""
    expected = os.environ.get("VIRALYST_ACCESS_CODE", "")
    if not expected:
        return True
    return code is not None and hmac.compare_digest(code.encode(), expected.encode())


def daily_budget() -> float | None:
    value = os.environ.get("VIRALYST_DAILY_BUDGET")
    return float(value) if value else None


class DailySpend:
    """Adds up today's AI spending (UTC days) so the server can refuse work beyond the budget.
    It lives in memory, so a restart resets it: a safety net, not a bank account. Also set a
    spending limit in the Anthropic Console."""

    def __init__(self, today=lambda: datetime.now(timezone.utc).date()):
        self.today = today  # a function, so tests can pretend it's tomorrow
        self.lock = threading.Lock()
        self.day = today()
        self.spent = 0.0

    def _roll_over(self) -> None:
        today = self.today()
        if today != self.day:
            self.day, self.spent = today, 0.0

    def spent_today(self) -> float:
        with self.lock:
            self._roll_over()
            return self.spent

    def can_spend(self, amount: float, budget: float | None) -> bool:
        if budget is None:
            return True
        with self.lock:
            self._roll_over()
            return self.spent + amount <= budget

    def record(self, amount: float) -> None:
        with self.lock:
            self._roll_over()
            self.spent += amount
