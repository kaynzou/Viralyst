"""Pull basic facts, frames and audio out of a video file, using ffmpeg.

ffmpeg and ffprobe are command-line programs. We run them from Python with
`subprocess`, exactly as if you typed the command in the Terminal.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

HOOK_SECONDS = 3  # people decide whether to keep watching in about this long


class MissingFFmpeg(RuntimeError):
    pass


@dataclass
class VideoFile:
    path: Path
    duration: float  # seconds
    width: int
    height: int
    has_audio: bool


def require_ffmpeg() -> None:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise MissingFFmpeg("ffmpeg isn't installed. Install it with: brew install ffmpeg")


def run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{command[0]} failed: {result.stderr.strip()[-500:]}")
    return result.stdout


def probe(path: str | Path) -> VideoFile:
    """Ask ffprobe how long the video is, how big, and whether it has sound."""
    require_ffmpeg()
    output = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                  "-of", "json", str(path)])
    info = json.loads(output)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise ValueError(f"{path} has no video track.")
    return VideoFile(
        path=Path(path),
        duration=float(info["format"]["duration"]),
        width=int(video["width"]),
        height=int(video["height"]),
        has_audio=any(s["codec_type"] == "audio" for s in info["streams"]),
    )


def frame_times(duration: float, max_after_hook: int = 10) -> list[float]:
    """Which moments to take pictures of. Every half second during the first 3 seconds,
    where people decide to scroll, then about one every 2 seconds (at most 10) after that."""
    hook = [i / 2 for i in range(HOOK_SECONDS * 2) if i / 2 < duration]
    remaining = duration - HOOK_SECONDS
    count = min(max_after_hook, int(remaining / 2))
    if count <= 0:
        return hook
    step = remaining / count
    return hook + [round(HOOK_SECONDS + step * (i + 0.5), 1) for i in range(count)]


def extract_frames(video: VideoFile, times: list[float], out_dir: Path, width: int = 512) -> list[tuple[float, Path]]:
    """Save one JPEG per moment, shrunk to `width` pixels wide (smaller images cost fewer tokens)."""
    frames = []
    for i, t in enumerate(times):
        out = out_dir / f"frame_{i:02d}.jpg"
        # -ss before -i jumps straight to that moment, which is much faster than decoding from the start.
        run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(video.path), "-frames:v", "1",
             "-vf", f"scale={width}:-2", "-q:v", "4", "-y", str(out)])
        if out.exists():  # a moment right at the very end may have no frame
            frames.append((t, out))
    return frames


def extract_audio(video: VideoFile, out: Path) -> Path:
    """Save the soundtrack as 16 kHz mono WAV, the format speech-to-text models expect."""
    run(["ffmpeg", "-v", "error", "-i", str(video.path), "-vn", "-ac", "1", "-ar", "16000", "-y", str(out)])
    return out
