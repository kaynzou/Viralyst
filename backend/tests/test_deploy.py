"""Tests for running online: allowed websites, the access code and the daily budget.
They pretend to be a deployed server with a made-up code and key, and never call Claude."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from viralyst import api
from viralyst.settings import CODE_HEADER, DailySpend, allowed_origins, code_is_valid

client = TestClient(api.app)
CODE = "test-code-not-real"


@pytest.fixture
def deployed(monkeypatch):
    """Settings like a real deployment: a key, an access code and a $1 daily budget."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("VIRALYST_ACCESS_CODE", CODE)
    monkeypatch.setenv("VIRALYST_DAILY_BUDGET", "1")
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)  # skip the wrong-code delay in tests
    monkeypatch.setattr(api, "SPEND", DailySpend())


def test_allowed_origins_always_include_local_development(monkeypatch):
    monkeypatch.delenv("VIRALYST_ALLOWED_ORIGINS", raising=False)
    assert allowed_origins() == ["http://localhost:3000"]
    monkeypatch.setenv("VIRALYST_ALLOWED_ORIGINS", "https://viralyst.vercel.app/, https://example.com")
    assert allowed_origins() == ["http://localhost:3000", "https://viralyst.vercel.app", "https://example.com"]


def test_without_a_configured_code_everything_is_open(monkeypatch):
    monkeypatch.delenv("VIRALYST_ACCESS_CODE", raising=False)
    assert code_is_valid(None)


def test_codes_must_match_exactly(monkeypatch):
    monkeypatch.setenv("VIRALYST_ACCESS_CODE", CODE)
    assert code_is_valid(CODE)
    assert not code_is_valid(None)
    assert not code_is_valid(CODE.upper())
    assert not code_is_valid(CODE + " ")


def test_daily_spend_resets_on_a_new_day():
    clock = {"today": date(2026, 10, 8)}
    spend = DailySpend(today=lambda: clock["today"])
    spend.record(0.8)
    assert not spend.can_spend(0.3, budget=1.0)
    clock["today"] = date(2026, 10, 9)
    assert spend.can_spend(0.3, budget=1.0)  # a new day starts from zero
    assert spend.can_spend(1000, budget=None)  # no budget configured: no limit


def test_status_shows_the_lock(deployed):
    locked = client.get("/api/status").json()
    assert locked["ai_available"] and locked["ai_locked"] and not locked["ai_unlocked"]
    assert locked["budget"] is None  # strangers don't see your spending

    unlocked = client.get("/api/status", headers={CODE_HEADER: CODE}).json()
    assert unlocked["ai_unlocked"] and unlocked["budget"] == {"limit": 1.0, "spent_today": 0.0}


def test_ai_needs_the_code(deployed):
    params = {"video": "examples/good_demo", "agent": "ai", "model": "claude-haiku-4-5"}
    assert client.get("/api/simulate", params=params).status_code == 403
    assert client.get("/api/simulate", params=params, headers={CODE_HEADER: "guess"}).status_code == 403


def test_the_budget_is_checked_before_spending(deployed, monkeypatch):
    monkeypatch.setenv("VIRALYST_DAILY_BUDGET", "0.01")  # far less than a full AI run could cost
    response = client.get("/api/simulate", headers={CODE_HEADER: CODE},
                          params={"video": "examples/good_demo", "agent": "ai", "model": "claude-haiku-4-5"})
    assert response.status_code == 429
    assert "budget" in response.json()["detail"]


def test_uploads_need_the_code(deployed):
    response = client.post("/api/analyze", files={"file": ("demo.mp4", b"fake", "video/mp4")})
    assert response.status_code == 403


def test_the_free_simulator_stays_open_to_everyone(deployed):
    response = client.get("/api/simulate", params={"video": "examples/good_demo", "seed": 1})
    assert response.status_code == 200
    assert client.get("/api/odds", params={"video": "examples/good_demo", "runs": 20}).status_code == 200


def test_only_allowed_websites_get_cors_permission():
    def preflight(origin: str):
        return client.options("/api/status", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})

    assert preflight("http://localhost:3000").headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in preflight("https://evil.example").headers
