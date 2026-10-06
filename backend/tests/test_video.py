"""Tests for Phase 4: reading a video, listening to it, and Claude's analysis (with fakes, so it's free)."""

import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile

from viralyst.media import extract_audio, extract_frames, frame_times, probe
from viralyst.speech import Transcript, Word, transcribe
from viralyst.video_analyzer import VideoAnalysis, analyze, build_content, clean, to_brief
from viralyst.voiceover import speak

BACKEND = Path(__file__).parent.parent
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg isn't installed")


@pytest.fixture(scope="module")
def tiny_video(tmp_path_factory) -> Path:
    """A 5-second test pattern with a beep, made by ffmpeg, so the tests don't need a real video."""
    path = tmp_path_factory.mktemp("video") / "tiny.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=10:duration=5",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=5", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(path)], check=True)
    return path


def test_frame_times_focus_on_the_first_3_seconds():
    times = frame_times(28)
    assert times[:6] == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]  # every half second during the hook
    assert len(times) == 6 + 10  # then at most 10 more
    assert all(3 <= t < 28 for t in times[6:])
    assert frame_times(2) == [0.0, 0.5, 1.0, 1.5]  # a very short video only has a hook


@needs_ffmpeg
def test_probe_reads_length_size_and_sound(tiny_video):
    video = probe(tiny_video)
    assert video.duration == pytest.approx(5, abs=0.2)
    assert (video.width, video.height) == (360, 640)
    assert video.has_audio


@needs_ffmpeg
def test_frames_and_audio_are_extracted(tiny_video, tmp_path):
    video = probe(tiny_video)
    frames = extract_frames(video, [0.0, 1.0, 4.0], tmp_path, width=180)
    assert [t for t, _ in frames] == [0.0, 1.0, 4.0]
    assert all(path.stat().st_size > 0 for _, path in frames)

    samples, rate = soundfile.read(str(extract_audio(video, tmp_path / "a.wav")))
    assert rate == 16000 and samples.ndim == 1  # 16 kHz mono, what Whisper expects


def test_transcribe_keeps_word_timings(tmp_path):
    audio = tmp_path / "silence.wav"
    soundfile.write(str(audio), np.zeros(16000, dtype="float32"), 16000)
    words = [SimpleNamespace(start=0.2, word=" Inbox"), SimpleNamespace(start=3.5, word=" zero")]
    segment = SimpleNamespace(start=0.0, end=4.0, text=" Inbox zero", words=words)
    fake_whisper = SimpleNamespace(transcribe=lambda samples, **_: (iter([segment]), SimpleNamespace(language="en")))

    transcript = transcribe(audio, model=fake_whisper)
    assert transcript.text == "Inbox zero"
    assert transcript.said_before(3) == "Inbox"


ANSWER = VideoAnalysis(hook="A counter drops", description="A demo.", topics=["productivity", "Email Things"],
                       hook_strength=0.8, quality=1.7, shareability=-0.2, save_value=0.5,
                       strengths=["fast"], weaknesses=["robotic voice"], better_hook="4,000 emails, gone.",
                       suggested_caption="inbox zero")


class FakeClaude:
    def __init__(self):
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **request):
        self.requests.append(request)
        usage = SimpleNamespace(input_tokens=9000, output_tokens=3000, cache_read_input_tokens=0, cache_creation_input_tokens=0)
        return SimpleNamespace(usage=usage, stop_reason="end_turn", parsed_output=ANSWER)


def test_claude_gets_labelled_frames_and_the_transcript(tmp_path):
    frame = tmp_path / "f.jpg"
    frame.write_bytes(b"\xff\xd8 not really a jpeg")
    video = SimpleNamespace(duration=12.0, width=540, height=960)
    transcript = Transcript("en", [], [Word(0.1, " Watch"), Word(0.4, " this"), Word(5.0, " later")])
    transcript.segments.append(SimpleNamespace(start=0.0, end=6.0, text="Watch this later"))

    content = build_content(video, [(0.0, frame), (0.5, frame)], transcript, "my caption")
    assert [c["type"] for c in content] == ["text", "image", "text", "image", "text"]
    assert content[0]["text"] == "Frame at 0.0s"
    assert content[1]["source"]["media_type"] == "image/jpeg"
    assert "Said in the first 3 seconds: Watch this" in content[-1]["text"]
    assert "my caption" in content[-1]["text"]


def test_analysis_is_cleaned_and_becomes_a_brief(tmp_path):
    video = SimpleNamespace(duration=12.6, width=540, height=960)
    analysis, usage = analyze(video, [], None, "", FakeClaude())
    assert analysis.topics == ["productivity"]  # the made-up tag is dropped
    assert analysis.quality == 1.0 and analysis.shareability == 0.0  # ratings forced into 0-1
    assert usage.cost > 0

    brief = to_brief(analysis, video, caption="")
    assert brief.title == "inbox zero"  # no caption given, so Claude's suggestion is used
    assert brief.length_seconds == 13


def test_a_video_with_no_known_topics_is_rejected():
    with pytest.raises(ValueError):
        clean(ANSWER.model_copy(update={"topics": ["nonsense"]}))


def test_voiceover_uses_the_first_voice_by_default(tmp_path):
    calls = {}
    fake_tts = SimpleNamespace(
        voice_style_names=["F1", "M1"],
        get_voice_style=lambda name: calls.setdefault("voice", name),
        synthesize=lambda text, voice_style, lang: (calls.setdefault("text", text), None),
        save_audio=lambda wav, path: Path(path).write_bytes(b"RIFF"),
    )
    out = speak("Inbox zero.", tmp_path / "hook.wav", tts=fake_tts)
    assert out.exists() and calls == {"voice": "F1", "text": "Inbox zero."}


def test_analyze_video_needs_a_key():
    no_key = {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", "ANTHROPIC_API_KEY": "", "ANTHROPIC_AUTH_TOKEN": ""}
    result = subprocess.run([sys.executable, "analyze_video.py", "examples/sample_demo.mp4", "--out", "x.json"],
                            cwd=BACKEND, capture_output=True, text=True, env=no_key)
    assert result.returncode != 0
    assert "No Claude API key found" in result.stderr or "ffmpeg isn't installed" in result.stderr
