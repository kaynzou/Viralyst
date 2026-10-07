"""Measure what a typical reel scores with a kind of persona, so the algorithm compares fairly.

    uv run measure_benchmarks.py --agent rules                         # free: check the numbers in the code
    uv run measure_benchmarks.py --agent ai --model claude-haiku-4-5   # measure AI personas (costs money)

AI results are saved to calibration/benchmarks.<model>.json and used automatically from then on.
"""

import argparse
import sys

from dotenv import load_dotenv

from viralyst import benchmarks
from viralyst.agent import MockAgent
from viralyst.algorithm import BENCHMARKS
from viralyst.claude import DEFAULT_MODEL, MISSING_KEY, PRICES, has_api_key
from viralyst.llm_agent import LLMAgent, estimate_cost
from viralyst.loading import load_example


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Measure the 'typical reel' benchmarks for a kind of persona.")
    parser.add_argument("--agent", choices=["rules", "ai"], default="rules")
    parser.add_argument("--model", choices=list(PRICES), default=DEFAULT_MODEL)
    parser.add_argument("--people", type=int, help="how many personas watch the typical reel "
                                                    "(default: 20,000 for rules, 300 for AI)")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()
    people = args.people or (20_000 if args.agent == "rules" else 300)

    if args.agent == "ai":
        if not has_api_key():
            sys.exit(MISSING_KEY)
        video, _ = load_example(benchmarks.TYPICAL_REEL)
        print(f"{people} AI personas ({args.model}) will watch the typical reel. "
              f"Estimated cost: up to ${estimate_cost(args.model, video, people):.2f}.")
        if not args.yes and input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Cancelled. Nothing was spent.")
            return
        agent = LLMAgent(args.model)
        agent.benchmarks = None  # measure from scratch, not against an older measurement
    else:
        agent = MockAgent()

    measured = benchmarks.measure(agent, people)
    current = BENCHMARKS if args.agent == "rules" else (benchmarks.load(args.model) or BENCHMARKS)
    print(f"\nTypical reel, watched by {people:,} {'rule-based' if args.agent == 'rules' else 'AI'} personas:")
    print(f"  {'signal':<9}{'in use now':>12}{'measured':>11}")
    for signal in BENCHMARKS:
        print(f"  {signal:<9}{current[signal]:>12.3f}{measured[signal]:>11.3f}")

    if args.agent == "ai":
        path = benchmarks.save(args.model, measured, people)
        print(f"\nSaved to {path.relative_to(benchmarks.BACKEND)}. AI runs with {args.model} now use these numbers.")
        print(agent.usage.summary())
    else:
        print("\nThe rule-based numbers live in viralyst/algorithm.py (BENCHMARKS). Update them there if they drift.")


if __name__ == "__main__":
    main()
