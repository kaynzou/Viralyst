"""Run a Viralyst simulation from the command line.

    uv run run.py examples/good_demo.json              # free rule-based personas
    uv run run.py examples/good_demo.json --seed 7     # repeat an exact run
    uv run run.py examples/good_demo.json --runs 200   # how often each outcome happens
    uv run run.py examples/good_demo.json --agent ai   # AI personas (asks before spending money)
    uv run run.py examples/good_demo.json --audience examples/other.audience.json
"""

import argparse
import random
import sys

import anthropic
from dotenv import load_dotenv

from viralyst.agent import MockAgent
from viralyst.calibration import load_model
from viralyst.claude import BAD_KEY, DEFAULT_MODEL, MISSING_KEY, PRICES, has_api_key
from viralyst.llm_agent import CACHE_DIR, LLMAgent, estimate_cost
from viralyst.loading import load_audience, load_example
from viralyst.models import VideoBrief
from viralyst.report import print_many_runs, print_report
from viralyst.simulation import WAVES, run_cascade
from viralyst.summary import furthest_stage


def confirm_cost(model: str, video: VideoBrief, runs: int) -> bool:
    calls = runs * sum(wave.size for wave in WAVES)
    print(f"This will ask up to {calls} AI personas using {model}.")
    print(f"Estimated cost: up to ${estimate_cost(model, video, calls):.2f}. Videos that stop early cost less,")
    print("and answers already saved on disk are free.")
    return input("Continue? [y/N] ").strip().lower() in ("y", "yes")


def print_calibrated_views(all_results: list, followers: int | None, agent_name: str) -> None:
    """With a calibration (see calibration/README.md), turn the odds into an estimate of real views."""
    model = load_model()
    if not model or model.agent != agent_name:
        if followers:
            print("No calibration for these personas yet, so no view estimate. See calibration/README.md.")
        return
    mean_stage = sum(furthest_stage(results) for results in all_results) / len(all_results)
    line = f"Calibrated on {model.videos} of your real videos: about {model.views_per_follower(mean_stage):.1f}x your follower count"
    if followers:
        line += f", so roughly {model.expected_views(mean_stage, followers):,.0f} views with {followers:,} followers"
    print(f"{line} (usually within {model.typical_miss:.1f}x).\n")


def main() -> None:
    load_dotenv()  # reads ANTHROPIC_API_KEY from backend/.env, if that file exists

    parser = argparse.ArgumentParser(description="Simulate how a video spreads on Instagram.")
    parser.add_argument("example", help="JSON file with a video brief and a target audience")
    parser.add_argument("--audience", help="use this audience file instead of the one in the example")
    parser.add_argument("--seed", type=int, help="fix the randomness so a run can be repeated exactly")
    parser.add_argument("--runs", type=int, default=1, help="run many simulations and show how often each outcome happens")
    parser.add_argument("--agent", choices=["rules", "ai"], default="rules",
                        help="rules: free formula-based personas. ai: Claude plays each persona (costs money)")
    parser.add_argument("--model", choices=list(PRICES), default=DEFAULT_MODEL, help="Claude model for --agent ai")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    parser.add_argument("--fresh", action="store_true", help="ask Claude again instead of reusing saved answers")
    parser.add_argument("--workers", type=int, default=8, help="how many AI personas to ask at the same time")
    parser.add_argument("--followers", type=int, help="your follower count, to estimate real views (needs calibration)")
    args = parser.parse_args()

    video, audience = load_example(args.example)
    if args.audience:
        audience = load_audience(args.audience)
    seed = args.seed if args.seed is not None else random.randrange(10_000)

    if args.agent == "ai":
        if not has_api_key():
            sys.exit(MISSING_KEY)
        if not args.yes and not confirm_cost(args.model, video, args.runs):
            print("Cancelled. Nothing was spent.")
            return
        agent = LLMAgent(args.model, args.workers, cache_dir=None if args.fresh else CACHE_DIR)
    else:
        agent = MockAgent()

    try:
        if args.runs == 1:
            print_report(video, run_cascade(video, audience, agent, seed), seed)
        else:
            all_results = [run_cascade(video, audience, agent, seed + i) for i in range(args.runs)]
            print_many_runs(video, all_results)
            print_calibrated_views(all_results, args.followers, "rules" if args.agent == "rules" else args.model)
    except anthropic.AuthenticationError:
        sys.exit(BAD_KEY)

    if args.agent == "ai":
        print(agent.usage.summary())


if __name__ == "__main__":
    main()
