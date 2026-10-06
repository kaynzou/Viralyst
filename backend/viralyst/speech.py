"""Speech-to-text: write down what's said in a video, using Whisper running on your Mac.

The audio never leaves your computer. The first run downloads the model
(about 150 MB for "base") and keeps it for next time.
"""

from dataclasses import dataclass
from pathlib import Path

import soundfile


@dataclass
class Segment:
    start: float  # seconds
    end: float
    text: str


@dataclass
class Word:
    start: float
    word: str


@dataclass
class Transcript:
    language: str
    segments: list[Segment]
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments)

    def said_before(self, seconds: float) -> str:
        """Exactly what's said in the opening seconds, word by word."""
        return "".join(w.word for w in self.words if w.start < seconds).strip()

    def timed(self) -> str:
        """One line per segment with its time, like "[0.0-2.4] I had 4,000 unread emails"."""
        return "\n".join(f"[{s.start:.1f}-{s.end:.1f}] {s.text}" for s in self.segments)


def transcribe(audio: Path, model_size: str = "base", model=None) -> Transcript:
    if model is None:
        # Imported here, not at the top: it's slow to load and only this function needs it.
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
    # Read the WAV ourselves and pass Whisper the raw samples. (Letting faster-whisper open the
    # file uses the `av` library, whose newest version is incompatible with it.)
    samples, rate = soundfile.read(str(audio), dtype="float32")
    if rate != 16000:
        raise ValueError(f"Expected 16 kHz audio from extract_audio(), got {rate} Hz.")
    segments, info = model.transcribe(samples, word_timestamps=True)
    segments = list(segments)  # Whisper does the work lazily; list() makes it finish now
    return Transcript(
        language=info.language,
        segments=[Segment(round(float(s.start), 1), round(float(s.end), 1), s.text.strip()) for s in segments],
        words=[Word(round(float(w.start), 2), w.word) for s in segments for w in (s.words or [])],
    )
