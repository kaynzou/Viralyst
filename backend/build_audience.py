"""Create an audience file from a plain-English description, using Claude.

    uv run build_audience.py "Solo founders building SaaS tools, mostly 22-35" --out examples/founders.audience.json

Then try any video with it:
    uv run run.py examples/good_demo.json --audience examples/founders.audience.json
"""

import argparse
import sys

import anthropic
from dotenv import load_dotenv

from viralyst.audience_builder import build_audience, estimate_build_cost
from viralyst.claude import BAD_KEY, DEFAULT_MODEL, MISSING_KEY, PRICES, has_api_key
from viralyst.loading import save_audience


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Turn a description of your audience into simulated people.")
    parser.add_argument("description", help='who the video is for, in plain English, inside "quotes"')
    parser.add_argument("--out", required=True, help="where to save the audience, e.g. examples/founders.audience.json")
    parser.add_argument("--count", type=int, default=12, help="how many kinds of people to create")
    parser.add_argument("--model", choices=list(PRICES), default=DEFAULT_MODEL, help="Claude model to use")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()

    if not has_api_key():
        sys.exit(MISSING_KEY)
    if not args.yes:
        print(f"This asks {args.model} once. Estimated cost: about ${estimate_build_cost(args.model, args.count):.2f}.")
        if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Cancelled. Nothing was spent.")
            return

    print("Asking Claude to build the audience (this can take a minute)...")
    try:
        audience, usage = build_audience(args.description, anthropic.Anthropic(max_retries=6), args.model, args.count)
    except anthropic.AuthenticationError:
        sys.exit(BAD_KEY)

    save_audience(audience, args.out)
    print(f"\nSaved {len(audience.archetypes)} kinds of people to {args.out}")
    print(f"Audience tags: {', '.join(audience.interests)}  |  ages {audience.min_age}-{audience.max_age}")
    for a in audience.archetypes:
        print(f"  {a.label:<32} {a.age:>2}, {a.location}")
    print(usage.summary())


if __name__ == "__main__":
    main()
