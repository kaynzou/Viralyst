"""Claude "watches" the video: it looks at frames, reads the transcript, and writes the video brief.

Claude can't take a video file directly, so we show it what a viewer would experience:
pictures from the video (many from the first 3 seconds) and what's said, with timestamps.
"""

import base64
from pathlib import Path

from pydantic import BaseModel

from .agent import clamp
from .claude import DEFAULT_MODEL, PRICES, Usage, fallback_options
from .media import HOOK_SECONDS, VideoFile
from .models import VideoBrief
from .personas import GENERAL_INTERESTS
from .speech import Transcript

INSTRUCTIONS = """\
You are an expert short-form video strategist reviewing a product demo before it's posted as an \
Instagram Reel. You'll see frames from the video with their timestamps (the first 3 seconds are \
sampled every half second, because that's when viewers decide whether to scroll), what is said, \
and how long it is.

Describe the video and rate it honestly. Most product demos are mediocre: a typical reel scores \
about 0.5 on each rating. Use the full range.

- hook: what a viewer sees and hears in the first 3 seconds, concretely.
- description: what happens across the whole video, including what's said and shown, in 2 to 4 sentences.
- topics: 1 to 3 tags from this list, spelled exactly like this: {tags}
- hook_strength (0-1): does the opening stop the scroll? 0.1 = a logo or slow intro, \
0.5 = clear but ordinary, 0.9 = an instant surprising payoff or question.
- quality (0-1): clarity, pacing, readable on-screen text, audio. 0.2 = confusing or slow, \
0.5 = fine, 0.9 = tight and polished.
- shareability (0-1): would people send it to a friend? 0.1 = a generic ad, \
0.5 = mildly interesting, 0.9 = surprising, funny, or "this is so you".
- save_value (0-1): is there something worth coming back to, like a tip, steps or a tool? \
0.1 = nothing, 0.9 = a genuinely useful reference.
- strengths and weaknesses: 2 to 4 short, specific points each.
- better_hook: one punchy sentence the creator could say in the first 3 seconds instead. \
Natural speech, under 15 words.
- suggested_caption: a short Instagram caption for the reel.
"""


class VideoAnalysis(BaseModel):
    hook: str
    description: str
    topics: list[str]
    hook_strength: float
    quality: float
    shareability: float
    save_value: float
    strengths: list[str]
    weaknesses: list[str]
    better_hook: str
    suggested_caption: str


def image_block(path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


def build_content(video: VideoFile, frames: list[tuple[float, Path]], transcript: Transcript | None, caption: str) -> list[dict]:
    """The user message: a label before each picture, then the transcript and the facts."""
    content = []
    for t, path in frames:
        content.append({"type": "text", "text": f"Frame at {t:.1f}s"})
        content.append(image_block(path))
    if transcript and transcript.segments:
        opening = transcript.said_before(HOOK_SECONDS) or "(nothing)"
        speech = f"{transcript.timed()}\n\nSaid in the first {HOOK_SECONDS} seconds: {opening}"
    else:
        speech = "No speech detected."
    content.append({"type": "text", "text": (
        f"What is said (from an automatic transcript):\n{speech}\n\n"
        f"Length: {video.duration:.0f} seconds.\n"
        f"The creator's caption: {caption or '(none yet)'}"
    )})
    return content


def clean(analysis: VideoAnalysis) -> VideoAnalysis:
    """Never trust a model's numbers blindly: keep ratings between 0 and 1 and topics in our tag list."""
    topics = [t for t in analysis.topics if t in GENERAL_INTERESTS]
    if not topics:
        raise ValueError("Claude didn't choose any known topic tags for this video.")
    return analysis.model_copy(update={
        "topics": topics,
        "hook_strength": clamp(analysis.hook_strength, 0.0, 1.0),
        "quality": clamp(analysis.quality, 0.0, 1.0),
        "shareability": clamp(analysis.shareability, 0.0, 1.0),
        "save_value": clamp(analysis.save_value, 0.0, 1.0),
    })


def to_brief(analysis: VideoAnalysis, video: VideoFile, caption: str) -> VideoBrief:
    return VideoBrief(
        title=caption or analysis.suggested_caption,
        hook=analysis.hook,
        description=analysis.description,
        topics=analysis.topics,
        length_seconds=max(1, round(video.duration)),
        hook_strength=analysis.hook_strength,
        quality=analysis.quality,
        shareability=analysis.shareability,
        save_value=analysis.save_value,
    )


def estimate_analysis_cost(model: str, video: VideoFile, frame_count: int) -> float:
    """A cautious estimate in dollars. An image costs about (width x height) / 750 tokens."""
    p = PRICES[model]
    image_tokens = 512 * (512 * video.height / video.width) / 750
    input_tokens = 1500 + frame_count * (image_tokens + 10)
    output_tokens = 4000  # the answer plus thinking
    return (input_tokens * p.input + output_tokens * p.output) / 1_000_000


def analyze(video: VideoFile, frames: list[tuple[float, Path]], transcript: Transcript | None, caption: str,
            client, model: str = DEFAULT_MODEL) -> tuple[VideoAnalysis, Usage]:
    usage = Usage(PRICES[model])
    response = client.beta.messages.parse(
        model=model,
        max_tokens=16000,
        system=INSTRUCTIONS.format(tags=", ".join(GENERAL_INTERESTS)),
        messages=[{"role": "user", "content": build_content(video, frames, transcript, caption)}],
        output_format=VideoAnalysis,
        **fallback_options(model),
    )
    usage.add(response.usage)
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise RuntimeError(f"Claude didn't return an analysis (stop reason: {response.stop_reason}).")
    return clean(response.parsed_output), usage
