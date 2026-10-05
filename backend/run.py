"""Run a Viralyst simulation from the command line.

    uv run run.py examples/good_demo.json
    uv run run.py examples/good_demo.json --seed 7
    uv run run.py examples/good_demo.json --runs 200
"""

import argparse
import json
import random

from viralyst.agent import MockAgent
from viralyst.models import Audience, VideoBrief
from viralyst.report import print_many_runs, print_report
from viralyst.simulation import run_cascade


def load_example(path: str) -> tuple[VideoBrief, Audience]:
    with open(path) as f:
        data = json.load(f)
    return VideoBrief(**data["video"]), Audience(**data["audience"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate how a video spreads on Instagram.")
    parser.add_argument("example", help="JSON file with a video brief and a target audience")
    parser.add_argument("--seed", type=int, help="fix the randomness so a run can be repeated exactly")
    parser.add_argument("--runs", type=int, default=1, help="run many simulations and show how often each outcome happens")
    args = parser.parse_args()

    video, audience = load_example(args.example)
    agent = MockAgent()
    seed = args.seed if args.seed is not None else random.randrange(10_000)

    if args.runs == 1:
        print_report(video, run_cascade(video, audience, agent, seed), seed)
    else:
        all_results = [run_cascade(video, audience, agent, seed + i) for i in range(args.runs)]
        print_many_runs(video, all_results)


if __name__ == "__main__":
    main()
