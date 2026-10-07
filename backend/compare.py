"""A/B test: which version of a video spreads further?

    uv run compare.py examples/weak_demo.json examples/good_demo.json
    uv run compare.py version_a.json version_b.json version_c.json --runs 500

The first video is the baseline (A); every other version is compared with it.
All versions are shown to the same audience with the same seeds.
"""

import argparse
import string
import sys

from dotenv import load_dotenv

from viralyst.agent import MockAgent
from viralyst.claude import DEFAULT_MODEL, MISSING_KEY, PRICES, has_api_key
from viralyst.experiments import compare, run_arm
from viralyst.llm_agent import LLMAgent, estimate_cost
from viralyst.loading import load_audience, load_example
from viralyst.simulation import WAVES

SHORT_STAGES = ["Flop", "Niche", "Solid", "Strong", "Viral"]


def percent(x: float) -> str:
    return f"{x:.0%}"


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Compare versions of a video on the same simulated audience.")
    parser.add_argument("videos", nargs="+", help="two to six video JSON files; the first is the baseline")
    parser.add_argument("--audience", help="audience file (default: the first video's audience)")
    parser.add_argument("--runs", type=int, default=200, help="simulations per version")
    parser.add_argument("--seed", type=int, default=0, help="first seed (each version uses the same seeds)")
    parser.add_argument("--agent", choices=["rules", "ai"], default="rules")
    parser.add_argument("--model", choices=list(PRICES), default=DEFAULT_MODEL)
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()

    if not 2 <= len(args.videos) <= 6:
        sys.exit("Give between two and six video files to compare.")
    briefs = [load_example(path) for path in args.videos]
    audience = load_audience(args.audience) if args.audience else briefs[0][1]

    if args.agent == "ai":
        if not has_api_key():
            sys.exit(MISSING_KEY)
        calls = len(briefs) * args.runs * sum(wave.size for wave in WAVES)
        cost = sum(estimate_cost(args.model, video, args.runs * sum(w.size for w in WAVES)) for video, _ in briefs)
        print(f"This could ask up to {calls:,} AI personas, costing up to ${cost:.2f}.")
        if not args.yes and input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Cancelled. Nothing was spent.")
            return
        agent = LLMAgent(args.model)
    else:
        agent = MockAgent()

    names = string.ascii_uppercase
    arms = [run_arm(names[i], video, audience, agent, args.runs, args.seed) for i, (video, _) in enumerate(briefs)]

    print()
    print(f"A/B TEST  {args.runs} simulations per version, same audience and seeds")
    print()
    print(f"{'':<3}{'Version':<40}" + "".join(f"{s:>7}" for s in SHORT_STAGES) + f"{'Breaks out (95% range)':>26}{'Avg stage':>11}")
    for arm in arms:
        title = arm.title if len(arm.title) <= 38 else arm.title[:37] + "…"
        low, high = arm.breakout_range
        breakout = f"{percent(arm.breakout_rate)} ({percent(low)}-{percent(high)})"
        print(f"{arm.name:<3}{title:<40}" + "".join(f"{percent(arm.odds[s]):>7}" for s in arm.odds)
              + f"{breakout:>26}{arm.mean_stage:>11.1f}")
    print()
    print("'Breaks out' = reaches the broad Reels audience (STRONG or VIRAL).")
    for challenger in arms[1:]:
        c = compare(arms[0], challenger)
        print(f"{challenger.name} vs A: {c.difference * 100:+.0f} points "
              f"(95% range {c.low * 100:+.0f} to {c.high * 100:+.0f}). {c.verdict}.")
    if args.agent == "ai":
        print(agent.usage.summary())
    print()


if __name__ == "__main__":
    main()
