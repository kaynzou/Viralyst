"""Tests for the web API. TestClient calls the API directly, without starting a server.
Nothing here uses a real API key or costs money."""

import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from viralyst import api
from viralyst.agent import MockAgent
from viralyst.loading import load_example
from viralyst.simulation import run_cascade
from viralyst.video_analyzer import VideoAnalysis

client = TestClient(api.app)


@pytest.fixture
def no_key(monkeypatch):
    # An empty variable that's already set is never replaced by backend/.env, so this holds
    # even after you add your real key.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "")


def read_events(response) -> list[dict]:
    """Split a Server-Sent Events stream back into its JSON events."""
    return [json.loads(line.removeprefix("data: ")) for line in response.text.splitlines() if line.startswith("data: ")]


def test_status_without_a_key(no_key):
    body = client.get("/api/status").json()
    assert body["ai_available"] is False
    assert "claude-opus-5-5" in body["models"]


def test_examples_lists_videos_and_audiences():
    body = client.get("/api/examples").json()
    ids = [v["id"] for v in body["videos"]]
    assert "examples/good_demo" in ids and "examples/weak_demo" in ids
    good = next(v for v in body["videos"] if v["id"] == "examples/good_demo")
    assert good["audience"] == "indie_founders" and good["length_seconds"] == 28
    assert body["audiences"][0]["id"] == "indie_founders"


def test_a_simulation_streams_start_waves_and_done():
    response = client.get("/api/simulate", params={"video": "examples/good_demo", "seed": 7})
    assert response.headers["content-type"].startswith("text/event-stream")
    events = read_events(response)
    assert [e["type"] for e in events] == ["start", "wave", "wave", "wave", "wave", "done"]
    assert len(events[1]["reactions"]) == 30
    # The stream must match the engine exactly: same seed, same scores as the terminal report.
    video, audience = load_example(api.EXAMPLES / "good_demo.json")
    expected = run_cascade(video, audience, MockAgent(), seed=7)
    assert [e["score"] for e in events[1:5]] == pytest.approx([w.score for w in expected])
    assert events[-1]["verdict"].startswith("VIRAL")
    assert events[-1]["usage"] is None  # the free agent spends nothing


def test_ai_simulation_without_a_key_is_refused(no_key):
    response = client.get("/api/simulate", params={"video": "examples/good_demo", "agent": "ai"})
    assert response.status_code == 400
    assert "No Claude API key found" in response.json()["detail"]


def test_only_known_files_can_be_opened():
    for sneaky in ["../../.env", "examples/../.env", "/etc/passwd"]:
        assert client.get("/api/simulate", params={"video": sneaky}).status_code == 404


def test_odds_add_up_to_one():
    body = client.get("/api/odds", params={"video": "examples/weak_demo", "runs": 50}).json()
    assert body["runs"] == 50
    assert sum(o["share"] for o in body["outcomes"]) == pytest.approx(1.0)
    assert body["outcomes"][0]["share"] > 0.9  # the weak demo almost always flops


def test_estimate_gives_a_cost():
    body = client.get("/api/estimate", params={"video": "examples/good_demo"}).json()
    assert body["max_calls"] == 450 and body["max_cost"] > 0


def test_analyzing_without_a_key_is_refused(no_key):
    response = client.post("/api/analyze", files={"file": ("demo.mp4", b"fake", "video/mp4")})
    assert response.status_code == 400
    assert "No Claude API key found" in response.json()["detail"]


ANSWER = VideoAnalysis(hook="A counter drops", description="A demo of an inbox tool.", topics=["productivity"],
                       hook_strength=0.8, quality=0.7, shareability=0.6, save_value=0.5, strengths=["fast"],
                       weaknesses=["robotic voice"], better_hook="4,000 emails, gone.", suggested_caption="inbox zero")


class FakeClaude:
    def __init__(self):
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **request):
        usage = SimpleNamespace(input_tokens=9000, output_tokens=3000, cache_read_input_tokens=0, cache_creation_input_tokens=0)
        return SimpleNamespace(usage=usage, stop_reason="end_turn", parsed_output=ANSWER)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg isn't installed")
def test_upload_analyze_then_simulate(tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=180x320:rate=5:duration=4",
                    "-f", "lavfi", "-i", "sine=duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest",
                    str(video)], check=True)
    monkeypatch.setattr(api, "UPLOADS", tmp_path / "uploads")  # keep test uploads out of the project
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")  # the fake Claude never uses it
    fake_transcribe = lambda audio, size: None  # noqa: E731 - pretend nothing is said
    api.app.dependency_overrides[api.claude_client] = FakeClaude
    api.app.dependency_overrides[api.speech_to_text] = lambda: fake_transcribe
    try:
        response = client.post("/api/analyze", data={"caption": "my clip"},
                               files={"file": ("clip.mp4", video.read_bytes(), "video/mp4")})
    finally:
        api.app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["video"]["title"] == "my clip" and body["analysis"]["better_hook"] == "4,000 emails, gone."
    assert body["id"] in [v["id"] for v in client.get("/api/examples").json()["videos"]]

    events = read_events(client.get("/api/simulate", params={"video": body["id"], "seed": 1}))
    assert events[-1]["type"] == "done"
