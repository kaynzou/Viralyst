"""Turn a real video file into a video brief that Viralyst can simulate.

    uv run analyze_video.py examples/sample_demo.mp4 --out examples/sample_demo.json
    uv run analyze_video.py my_reel.mp4 --caption "my caption" --out examples/my_reel.json --voiceover

Then simulate it like any other example:
    uv run run.py examples/my_reel.json
"""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from viralyst.claude import BAD_KEY, DEFAULT_MODEL, MISSING_KEY, PRICES, has_api_key
from viralyst.media import MissingFFmpeg, extract_audio, extract_frames, frame_times, probe, require_ffmpeg
from viralyst.speech import transcribe
from viralyst.video_analyzer import analyze, estimate_analysis_cost, to_brief

DEFAULT_AUDIENCE = "examples/indie_founders.audience.json"


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Turn a video file into a Viralyst video brief.")
    parser.add_argument("video", help="the video file, e.g. my_reel.mp4")
    parser.add_argument("--out", required=True, help="where to save the result, e.g. examples/my_reel.json")
    parser.add_argument("--caption", default="", help="the caption you plan to post with it")
    parser.add_argument("--audience", default=DEFAULT_AUDIENCE, help="audience file the video is aimed at")
    parser.add_argument("--model", choices=list(PRICES), default=DEFAULT_MODEL, help="Claude model that watches the video")
    parser.add_argument("--whisper", default="base", choices=["tiny", "base", "small"],
                        help="speech-to-text model size: bigger is more accurate but slower")
    parser.add_argument("--voiceover", action="store_true", help="also record the suggested opening line with Supertonic")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()

    try:
        require_ffmpeg()
    except MissingFFmpeg as error:
        sys.exit(str(error))
    if not has_api_key():
        sys.exit(MISSING_KEY)

    video = probe(args.video)
    print(f"Video: {video.duration:.1f}s, {video.width}x{video.height}, {'with' if video.has_audio else 'no'} sound")

    with tempfile.TemporaryDirectory() as work:  # a scratch folder that's deleted afterwards
        frames = extract_frames(video, frame_times(video.duration), Path(work))
        print(f"Took {len(frames)} frames ({sum(t < 3 for t, _ in frames)} from the first 3 seconds)")

        transcript = None
        if video.has_audio:
            print("Listening with Whisper (the first run downloads its model, about 150 MB)...")
            transcript = transcribe(extract_audio(video, Path(work) / "audio.wav"), args.whisper)
            print(f"Heard: {transcript.text[:200] or '(no speech)'}")

        if not args.yes:
            cost = estimate_analysis_cost(args.model, video, len(frames))
            print(f"Claude ({args.model}) will look at the frames and transcript. Estimated cost: about ${cost:.2f}.")
            if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
                print("Cancelled. Nothing was spent.")
                return

        print("Claude is watching the video...")
        try:
            analysis, usage = analyze(video, frames, transcript, args.caption, anthropic.Anthropic(max_retries=6), args.model)
        except anthropic.AuthenticationError:
            sys.exit(BAD_KEY)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "audience": os.path.relpath(args.audience, out.parent),  # stored relative to the output file
        "video": asdict(to_brief(analysis, video, args.caption)),
        "analysis": {
            "source": str(args.video),
            "analyzed_on": date.today().isoformat(),
            "model": args.model,
            "transcript": transcript.text if transcript else "",
            "strengths": analysis.strengths,
            "weaknesses": analysis.weaknesses,
            "better_hook": analysis.better_hook,
            "suggested_caption": analysis.suggested_caption,
        },
    }
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    print(f"\nSaved the brief to {out}")
    print(f"Hook: {analysis.hook}")
    print(f"Ratings: hook {analysis.hook_strength:.2f} | quality {analysis.quality:.2f} | "
          f"shareability {analysis.shareability:.2f} | save value {analysis.save_value:.2f}")
    print("Strengths:\n" + "\n".join(f"  + {s}" for s in analysis.strengths))
    print("Weaknesses:\n" + "\n".join(f"  - {w}" for w in analysis.weaknesses))
    print(f'Try this opening line instead: "{analysis.better_hook}"')
    print(usage.summary())

    if args.voiceover:
        from viralyst.voiceover import speak
        print("Recording the new opening line with Supertonic (the first run downloads its model)...")
        audio = speak(analysis.better_hook, out.with_suffix(".hook.wav"))
        print(f"Voiceover saved to {audio}")

    print(f"\nNext: uv run run.py {out}")


if __name__ == "__main__":
    main()
