"""The steps from a video file to a saved video brief, shared by analyze_video.py and the website."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .media import VideoFile, extract_audio, extract_frames, frame_times, probe
from .speech import Transcript, transcribe
from .video_analyzer import VideoAnalysis, to_brief


@dataclass
class PreparedVideo:
    """Everything Claude needs to see, gathered for free on this computer."""

    video: VideoFile
    frames: list[tuple[float, Path]]
    transcript: Transcript | None


def prepare(path: str | Path, work_dir: Path, whisper: str = "base", transcriber=transcribe) -> PreparedVideo:
    """Facts, frames and transcript. `transcriber` can be swapped for a fake in tests."""
    video = probe(path)
    frames = extract_frames(video, frame_times(video.duration), work_dir)
    transcript = transcriber(extract_audio(video, work_dir / "audio.wav"), whisper) if video.has_audio else None
    return PreparedVideo(video, frames, transcript)


def build_result(prepared: PreparedVideo, analysis: VideoAnalysis, caption: str, audience_path: Path,
                 out_path: Path, model: str) -> dict:
    """The JSON saved for an analyzed video: the brief to simulate, plus Claude's feedback."""
    return {
        "audience": os.path.relpath(audience_path, out_path.parent),  # stored relative to the output file
        "video": asdict(to_brief(analysis, prepared.video, caption)),
        "analysis": {
            "source": prepared.video.path.name,
            "analyzed_on": date.today().isoformat(),
            "model": model,
            "transcript": prepared.transcript.text if prepared.transcript else "",
            "strengths": analysis.strengths,
            "weaknesses": analysis.weaknesses,
            "better_hook": analysis.better_hook,
            "suggested_caption": analysis.suggested_caption,
        },
    }


def save_result(result: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
