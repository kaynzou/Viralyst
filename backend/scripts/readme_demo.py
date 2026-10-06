"""Make the animated Phase 4 demo for the README (docs/images/phase4-demo.gif).

    cd backend
    uv run scripts/readme_demo.py

Everything in it is real output: the frames come from media.py and the words
(with their timings) from Whisper via speech.py.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from viralyst.media import HOOK_SECONDS, extract_audio, extract_frames, frame_times, probe  # noqa: E402
from viralyst.speech import transcribe  # noqa: E402

VIDEO = BACKEND / "examples" / "sample_demo.mp4"
OUT = BACKEND.parent / "docs" / "images" / "phase4-demo.gif"
W, H, FPS, HOLD_SECONDS = 960, 560, 10, 3
BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, DIM, BLUE = "#e6edf3", "#8b949e", "#58a6ff"
RIGHT = 330  # where the right-hand panel starts
THUMB_W, THUMB_H, THUMB_GAP = 48, 85, 6


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def draw_words(draw: ImageDraw.ImageDraw, words, t: float) -> None:
    """Write the words heard so far, wrapping lines, with the hook's words in blue."""
    f, x, y, max_x = font(21), RIGHT, 285, W - 36
    for word in words:
        if word.start > t:
            break
        text = word.word.strip() + " "
        width = draw.textlength(text, font=f)
        if x + width > max_x:
            x, y = RIGHT, y + 32
        draw.text((x, y), text, font=f, fill=BLUE if word.start < HOOK_SECONDS else TEXT)
        x += width


def compose(t: float, video_frame: Image.Image, thumbs, words, length: float, finished: bool) -> Image.Image:
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)

    image.paste(video_frame, (30, 40))
    draw.rectangle((29, 39, 30 + video_frame.width, 40 + video_frame.height), outline=BORDER)

    draw.text((RIGHT, 32), "What Viralyst sees", font=font(24), fill=TEXT)
    draw.text((RIGHT, 64), "frames from ffmpeg: every 0.5s during the hook, then about every 2s", font=font(15), fill=DIM)
    for i, (when, thumb) in enumerate(thumbs):
        x = RIGHT + i * (THUMB_W + THUMB_GAP)
        draw.rectangle((x - 1, 99, x + THUMB_W, 100 + THUMB_H), outline=BORDER)
        if when <= t:
            image.paste(thumb, (x, 100))
            just_taken = t - when < 0.4
            draw.rectangle((x - 2, 98, x + THUMB_W + 1, 101 + THUMB_H),
                           outline=BLUE if when < HOOK_SECONDS or just_taken else BORDER, width=2 if just_taken else 1)
        draw.text((x + THUMB_W / 2, 192), f"{when:g}s", font=font(12), fill=DIM, anchor="mt")

    draw.text((RIGHT, 222), "What Viralyst hears", font=font(24), fill=TEXT)
    draw.text((RIGHT, 254), "speech-to-text by Whisper, running on this Mac (blue = said in the first 3 seconds)",
              font=font(15), fill=DIM)
    draw_words(draw, words, t)

    # Timeline with the hook zone shaded
    left, right, y = RIGHT, W - 36, 462
    scale = (right - left) / length
    draw.rectangle((left, y, right, y + 6), fill=PANEL, outline=BORDER)
    draw.rectangle((left, y, left + HOOK_SECONDS * scale, y + 6), fill="#1f3a5f")
    draw.text((left + HOOK_SECONDS * scale / 2, y - 6), "the hook", font=font(13), fill=BLUE, anchor="mb")
    playhead = left + min(t, length) * scale
    draw.ellipse((playhead - 7, y - 4, playhead + 7, y + 10), fill=TEXT)
    for second, label in [(0, "0s"), (HOOK_SECONDS, f"{HOOK_SECONDS}s"), (length, f"{length:.0f}s")]:
        draw.text((left + second * scale, y + 16), label, font=font(13), fill=DIM, anchor="mt")

    if finished:
        box_right = W - 26
        draw.rounded_rectangle((RIGHT - 10, 498, box_right, 548), radius=8, fill=PANEL, outline=BORDER)
        lines = [(f"Next: these {len(thumbs)} frames + the transcript go to Claude, which writes the brief:", TEXT),
                 ("hook, ratings, strengths, weaknesses and a better opening line that Supertonic reads aloud.", DIM)]
        for row, (text, color) in enumerate(lines):
            size = 15
            while draw.textlength(text, font=font(size)) > box_right - RIGHT - 10:  # shrink until it fits
                size -= 1
            draw.text((RIGHT, 507 + row * 20), text, font=font(size), fill=color)
    return image


def main() -> None:
    video = probe(VIDEO)
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        frames = extract_frames(video, frame_times(video.duration), work)
        thumbs = [(t, Image.open(p).resize((THUMB_W, THUMB_H))) for t, p in frames]
        words = transcribe(extract_audio(video, work / "audio.wav")).words

        playback = work / "playback"
        playback.mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(VIDEO), "-vf", f"fps={FPS},scale=270:480",
                        str(playback / "%04d.png")], check=True)
        video_frames = sorted(playback.glob("*.png"))

        composed = work / "composed"
        composed.mkdir()
        total = len(video_frames) + HOLD_SECONDS * FPS  # hold the last frame at the end
        for i in range(total):
            t = i / FPS
            frame = Image.open(video_frames[min(i, len(video_frames) - 1)]).convert("RGB")
            compose(t, frame, thumbs, words, video.duration, finished=i >= len(video_frames)).save(composed / f"{i:04d}.png")

        # Two passes make a good GIF: first find the best 128 colors, then use them.
        palette = work / "palette.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(composed / "%04d.png"),
                        "-vf", "palettegen=max_colors=128", str(palette)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(composed / "%04d.png"),
                        "-i", str(palette), "-lavfi", "paletteuse=dither=bayer:bayer_scale=5", "-loop", "0",
                        str(OUT)], check=True)
    print(f"Saved {OUT.relative_to(BACKEND.parent)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
