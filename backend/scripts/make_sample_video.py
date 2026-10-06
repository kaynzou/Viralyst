"""Make a short sample product-demo video to test Viralyst with (macOS only).

    cd backend
    uv run scripts/make_sample_video.py

The pictures are drawn with Pillow, the voiceover comes from the Mac's built-in `say`
command, and ffmpeg joins them into examples/sample_demo.mp4.
"""

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BACKEND = Path(__file__).resolve().parent.parent
OUT = BACKEND / "examples" / "sample_demo.mp4"
WIDTH, HEIGHT, FPS = 540, 960, 15
SCRIPT = ("I had four thousand two hundred unread emails. Watch this. One click, and the AI sorts everything, "
          "drafts my replies, and archives the newsletters. Inbox zero in thirty seconds. Link in bio.")


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def centered(draw: ImageDraw.ImageDraw, y: int, text: str, size: int, fill: str) -> None:
    f = font(size)
    left, _, right, _ = draw.textbbox((0, 0), text, font=f)
    draw.text(((WIDTH - (right - left)) / 2, y), text, font=f, fill=fill)


def draw_frame(t: float, length: float) -> Image.Image:
    if t < 3:  # the hook: an inbox counter dropping fast
        image = Image.new("RGB", (WIDTH, HEIGHT), "white")
        draw = ImageDraw.Draw(image)
        centered(draw, 120, "watch this", 44, "#222222")
        centered(draw, 360, f"{int(4212 - 370 * t):,}", 130, "#d93025")
        centered(draw, 530, "unread emails", 40, "#555555")
    elif t < 7.5:  # the demo: the tool working through the inbox
        image = Image.new("RGB", (WIDTH, HEIGHT), "#f1f3f4")
        draw = ImageDraw.Draw(image)
        centered(draw, 110, "one click", 56, "#222222")
        centered(draw, 200, f"{max(0, int(3100 - 700 * (t - 3))):,} unread", 36, "#d93025")
        steps = ["sorting everything", "drafting replies", "archiving newsletters"]
        for i, step in enumerate(steps):
            done = t > 3.8 + i * 1.2
            color = "#1e8e3e" if done else "#888888"
            f = font(38)
            text_width = draw.textbbox((0, 0), step, font=f)[2]
            x, y = (WIDTH - text_width - 40) / 2, 360 + i * 120
            # A dot instead of a ✓, because the default font has no tick symbol.
            draw.ellipse((x, y + 12, x + 24, y + 36), fill=color)
            draw.text((x + 40, y), step, font=f, fill=color)
    else:  # the payoff
        image = Image.new("RGB", (WIDTH, HEIGHT), "#1e8e3e")
        draw = ImageDraw.Draw(image)
        centered(draw, 360, "Inbox: 0", 100, "white")
        centered(draw, 520, "in 30 seconds", 44, "white")
        centered(draw, 780, "link in bio", 36, "#d2f5dc")
    return image


def main() -> None:
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        voice = work / "voice.aiff"
        subprocess.run(["say", "-v", "Samantha", "-o", str(voice), SCRIPT], check=True)
        voice_length = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(voice)],
            capture_output=True, text=True, check=True).stdout)
        length = round(voice_length + 0.8, 1)

        for i in range(int(length * FPS)):
            draw_frame(i / FPS, length).save(work / f"frame_{i:04d}.png")

        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(work / "frame_%04d.png"),
                        "-i", str(voice), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30",
                        "-c:a", "aac", "-b:a", "64k", "-t", str(length), str(OUT)], check=True)
    print(f"Saved {OUT.relative_to(BACKEND)} ({length:.1f}s, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
