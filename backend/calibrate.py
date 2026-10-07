"""Check Viralyst's predictions against your real Instagram results (see calibration/README.md).

    uv run calibrate.py calibration/results.csv
    uv run calibrate.py calibration/results.csv --runs 500

Saves calibration/model.json. After that, `run.py ... --runs 200 --followers 1200`
estimates real views for a new video.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from viralyst.agent import MockAgent
from viralyst.calibration import (MODEL_PATH, TRUSTWORTHY_VIDEOS, calibrate, load_results, save_model,
                                  simulate_points)
from viralyst.claude import DEFAULT_MODEL, MISSING_KEY, PRICES, has_api_key
from viralyst.llm_agent import LLMAgent, estimate_cost
from viralyst.loading import load_example
from viralyst.simulation import WAVES


def describe_correlation(rho: float) -> str:
    if rho >= 0.7:
        return "Viralyst ranks your videos in roughly the right order. Good."
    if rho >= 0.4:
        return "Some agreement: videos it rates higher tend to do better, with exceptions."
    if rho > 0:
        return "Weak: the predictions barely track reality yet."
    return "No agreement or backwards: don't trust the predictions for this account yet."


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Compare simulated predictions with real Instagram results.")
    parser.add_argument("results", help="CSV with columns video,followers,views (see calibration/README.md)")
    parser.add_argument("--runs", type=int, default=200, help="simulations per video")
    parser.add_argument("--agent", choices=["rules", "ai"], default="rules")
    parser.add_argument("--model", choices=list(PRICES), default=DEFAULT_MODEL)
    parser.add_argument("--out", default=str(MODEL_PATH), help="where to save the fitted model")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()

    try:
        results = load_results(args.results)
    except (ValueError, KeyError) as error:
        sys.exit(f"Couldn't read {args.results}: {error}")
    if not results:
        sys.exit(f"{args.results} has no videos yet. See calibration/README.md for how to fill it in.")

    if args.agent == "ai":
        if not has_api_key():
            sys.exit(MISSING_KEY)
        calls = len(results) * args.runs * sum(w.size for w in WAVES)
        cost = sum(estimate_cost(args.model, load_example(Path(r.video))[0], args.runs * sum(w.size for w in WAVES))
                   for r in results)
        print(f"This could ask up to {calls:,} AI personas, costing up to ${cost:.2f}. Consider a small --runs.")
        if not args.yes and input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Cancelled. Nothing was spent.")
            return
        agent, agent_name = LLMAgent(args.model), args.model
    else:
        agent, agent_name = MockAgent(), "rules"

    points = simulate_points(results, agent, args.runs)
    try:
        model = calibrate(points, agent_name)
    except ValueError as error:
        sys.exit(str(error))

    print(f"\nCALIBRATION  {len(points)} real videos, {args.runs} simulations each ({agent_name} personas)\n")
    print(f"{'Video':<40}{'Followers':>10}{'Real views':>12}{'Per follower':>14}{'Sim. stage':>12}{'Fitted views':>14}")
    for p in points:
        title = p.title if len(p.title) <= 38 else p.title[:37] + "…"
        fitted = model.expected_views(p.mean_stage, p.followers)
        print(f"{title:<40}{p.followers:>10,}{p.views:>12,}{p.views_per_follower:>13.1f}x{p.mean_stage:>12.1f}{fitted:>14,.0f}")

    print(f"\nRanking check (Spearman): {model.spearman:+.2f}. {describe_correlation(model.spearman)}")
    stages = "  ".join(f"stage {s}: {model.views_per_follower(s):.1f}x" for s in (1, 3, 5))
    print(f"Scale (views per follower): {stages}")
    print(f"Honest accuracy (leave-one-out): predictions are typically within {model.typical_miss:.1f}x of real views.")
    if len(points) < TRUSTWORTHY_VIDEOS:
        print(f"Only {len(points)} videos: treat this as a rough first guess. {TRUSTWORTHY_VIDEOS}+ is much better.")

    save_model(model, Path(args.out))
    print(f"\nSaved {args.out}. Now try: uv run run.py examples/good_demo.json --runs 200 --followers 1200")


if __name__ == "__main__":
    main()
