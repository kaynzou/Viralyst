"""Regenerate the pictures used in the README.

    cd backend
    uv run scripts/readme_images.py

Writes SVG files to docs/images/. SVG is an image format made of text
(shapes and words), so we can draw pictures with plain Python strings.
"""

import random
import subprocess
import sys
from html import escape
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
IMAGES = BACKEND.parent / "docs" / "images"
sys.path.insert(0, str(BACKEND))  # lets this script import the viralyst package

from viralyst.simulation import WAVES  # noqa: E402

BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, DIM, BLUE, GREEN, RED, GRAY = "#e6edf3", "#8b949e", "#58a6ff", "#3fb950", "#f85149", "#484f58"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


# ---------- Terminal screenshots ----------

def run_cli(*args: str) -> str:
    result = subprocess.run([sys.executable, "run.py", *args], cwd=BACKEND, capture_output=True, text=True, check=True)
    return result.stdout.strip("\n")


def line_color(line: str) -> str:
    if line.startswith("$") or line.startswith("Wave "):
        return DIM
    if line.startswith("VIRALYST"):
        return BLUE
    if "stop (needs" in line or "FLOP" in line or "#1 problem" in line:
        return RED
    if "push (needs" in line or "VIRAL" in line or "STRONG" in line:
        return GREEN
    return TEXT


def terminal_svg(commands: list[str]) -> str:
    lines = []
    for command in commands:
        lines.append(f"$ uv run run.py {command}")
        lines.extend(run_cli(*command.split()).splitlines())
        lines.append("")
    lines.pop()

    char_w, line_h, pad, bar = 7.8, 18, 20, 34
    width = round(max(len(line) for line in lines) * char_w + 2 * pad)
    height = bar + 2 * pad + len(lines) * line_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}"/>',
        f'<path d="M0 10a10 10 0 0 1 10-10h{width - 20}a10 10 0 0 1 10 10v{bar - 10}h-{width}z" fill="{PANEL}"/>',
        f'<line x1="0" y1="{bar}" x2="{width}" y2="{bar}" stroke="{BORDER}"/>',
        *(f'<circle cx="{20 + i * 20}" cy="{bar / 2}" r="6" fill="{c}"/>' for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"])),
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="none" stroke="{BORDER}"/>',
        f'<g font-family="{MONO}" font-size="13" xml:space="preserve" style="white-space:pre">',
    ]
    for i, line in enumerate(lines):
        y = bar + pad + (i + 1) * line_h - 4
        # &#160; is a non-breaking space: unlike a normal space, SVG never collapses it,
        # so the table columns stay lined up.
        parts.append(f'<text x="{pad}" y="{y}" fill="{line_color(line)}">{escape(line).replace(" ", "&#160;")}</text>')
    parts += ["</g>", "</svg>"]
    return "\n".join(parts)


# ---------- "How it works" diagram ----------

def cascade_svg() -> str:
    rng = random.Random(4)
    gap, per_row = 9, 10  # dot spacing, dots per row
    col_w, arrow_w, box_w, margin = gap * per_row, 62, 124, 24
    top = 96
    base = top + max(w.size for w in WAVES) // per_row * gap  # bottom edge of the dot grids
    arrow_y = base - 15
    width = 2 * margin + 2 * box_w + len(WAVES) * col_w + (len(WAVES) + 1) * arrow_w
    height = base + 120

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{SANS}">',
        '<defs><marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0 0L10 5L0 10z" fill="{DIM}"/></marker></defs>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="{margin}" y="44" fill="{TEXT}" font-size="20" font-weight="600">How a video spreads in Viralyst</text>',
        f'<text x="{margin}" y="68" fill="{DIM}" font-size="14">Each wave is bigger and has more strangers. '
        'The video only reaches the next wave if this one beats a typical reel.</text>',
    ]

    def box(x: float, title: str, lines: list[str]) -> None:
        y = arrow_y - 45
        parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="90" rx="10" fill="{PANEL}" stroke="{BORDER}"/>')
        parts.append(f'<text x="{x + box_w / 2}" y="{y + 32}" fill="{TEXT}" font-size="15" font-weight="600" text-anchor="middle">{title}</text>')
        for i, line in enumerate(lines):
            parts.append(f'<text x="{x + box_w / 2}" y="{y + 54 + i * 17}" fill="{DIM}" font-size="12" text-anchor="middle">{line}</text>')

    def arrow(x1: float, label: str = "") -> None:
        parts.append(f'<line x1="{x1 + 8}" y1="{arrow_y}" x2="{x1 + arrow_w - 8}" y2="{arrow_y}" stroke="{DIM}" stroke-width="1.5" marker-end="url(#head)"/>')
        if label:
            parts.append(f'<text x="{x1 + arrow_w / 2}" y="{arrow_y - 10}" fill="{GREEN}" font-size="11" text-anchor="middle">{label}</text>')

    x = margin
    box(x, "Video brief", ["hook · quality", "topics · length"])
    x += box_w
    arrow(x)
    x += arrow_w

    for number, wave in enumerate(WAVES, start=1):
        in_target = round(wave.size * wave.target_fraction)
        colors = [BLUE] * in_target + [GRAY] * (wave.size - in_target)
        rng.shuffle(colors)
        for i, color in enumerate(colors):
            row, col = divmod(i, per_row)
            parts.append(f'<circle cx="{x + col * gap + gap / 2}" cy="{base - row * gap - gap / 2}" r="3.2" fill="{color}"/>')
        center = x + col_w / 2
        parts.append(f'<text x="{center}" y="{base + 26}" fill="{TEXT}" font-size="13" font-weight="600" text-anchor="middle">Wave {number}</text>')
        parts.append(f'<text x="{center}" y="{base + 44}" fill="{DIM}" font-size="12" text-anchor="middle">{wave.label}</text>')
        parts.append(f'<text x="{center}" y="{base + 61}" fill="{DIM}" font-size="12" text-anchor="middle">{wave.size} people · {wave.target_fraction:.0%} target</text>')
        x += col_w
        arrow(x, "score ≥ 1.0" if number < len(WAVES) else "")
        x += arrow_w

    box(x, "Report", ["how far it got", "who engaged · tips"])

    legend_y = height - 22
    parts += [
        f'<circle cx="{margin + 5}" cy="{legend_y - 4}" r="4" fill="{BLUE}"/>',
        f'<text x="{margin + 16}" y="{legend_y}" fill="{DIM}" font-size="12">in your target audience</text>',
        f'<circle cx="{margin + 175}" cy="{legend_y - 4}" r="4" fill="{GRAY}"/>',
        f'<text x="{margin + 186}" y="{legend_y}" fill="{DIM}" font-size="12">everyone else</text>',
        f'<text x="{width - margin}" y="{legend_y}" fill="{DIM}" font-size="12" text-anchor="end">'
        'A wave that scores below 1.0 ends the spread.</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    images = {
        "how-it-works.svg": cascade_svg(),
        "report.svg": terminal_svg(["examples/good_demo.json --seed 7"]),
        "odds.svg": terminal_svg(["examples/weak_demo.json --runs 200 --seed 0",
                                  "examples/good_demo.json --runs 200 --seed 0"]),
    }
    for name, svg in images.items():
        (IMAGES / name).write_text(svg + "\n")
        print(f"wrote docs/images/{name}")


if __name__ == "__main__":
    main()
