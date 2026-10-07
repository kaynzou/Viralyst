"""Check predictions against real Instagram results, and learn to estimate real views.

You record real numbers for videos you've posted (calibration/results.csv). Viralyst
simulates each video many times and takes its average stage (1 = flop ... 5 = viral).
Then two questions:
  1. Ranking: do videos with a higher simulated stage really get more views?
  2. Scale: how many real views per follower does each stage mean for your account?
"""

import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean, median

from .experiments import run_arm
from .loading import load_example

BACKEND = Path(__file__).resolve().parent.parent
MODEL_PATH = BACKEND / "calibration" / "model.json"
MIN_VIDEOS = 5  # fewer than this and a line can't be fitted meaningfully
TRUSTWORTHY_VIDEOS = 10  # below this, treat the result as a rough first guess


@dataclass
class RealResult:
    video: str  # the video's brief, a path relative to backend/
    followers: int  # your follower count when it was posted
    views: int  # real views from Instagram Insights


@dataclass
class Point:
    """One real video: what really happened, next to what the simulation predicted."""

    title: str
    followers: int
    views: int
    mean_stage: float

    @property
    def views_per_follower(self) -> float:
        return self.views / self.followers

    @property
    def log_ratio(self) -> float:
        # Views vary hugely (300 vs 300,000), so we compare them on a log scale: each +1 means 10x more.
        return math.log10(self.views_per_follower)


def load_results(path: str | Path) -> list[RealResult]:
    results = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            video = (row.get("video") or "").strip()
            if not video or video.startswith("#"):
                continue  # blank lines and comments
            followers, views = int(row["followers"]), int(row["views"])
            if followers <= 0 or views <= 0:
                raise ValueError(f"{video}: followers and views must be above zero.")
            results.append(RealResult(video, followers, views))
    return results


def simulate_points(results: list[RealResult], agent, runs: int, seed: int = 0) -> list[Point]:
    points = []
    for real in results:
        video, audience = load_example(BACKEND / real.video)
        arm = run_arm("", video, audience, agent, runs, seed)
        points.append(Point(video.title, real.followers, real.views, arm.mean_stage))
    return points


# ---------- The statistics, written out so you can see how they work ----------

def fit_line(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """The straight line closest to the points ("least squares"): returns (intercept, slope)."""
    mx, my = mean(xs), mean(ys)
    spread = sum((x - mx) ** 2 for x in xs)
    if spread == 0:  # every x is the same, so there's no slope to learn
        return my, 0.0
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / spread
    return my - slope * mx, slope


def ranks(values: list[float]) -> list[float]:
    """Position of each value when sorted (1 = smallest). Tied values share their average position."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            result[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return result


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation: +1 = same order exactly, 0 = no relation, -1 = exactly backwards."""
    return pearson(ranks(xs), ranks(ys))


def leave_one_out_miss(points: list[Point]) -> float:
    """An honest accuracy check: predict each video using a line fitted on all the *other* videos.
    Returns the typical miss as a factor: 2.0 means "usually within 2x of the real views"."""
    errors = []
    for i, held_out in enumerate(points):
        others = points[:i] + points[i + 1:]
        intercept, slope = fit_line([p.mean_stage for p in others], [p.log_ratio for p in others])
        errors.append(abs(intercept + slope * held_out.mean_stage - held_out.log_ratio))
    return 10 ** median(errors)


@dataclass
class CalibrationModel:
    intercept: float
    slope: float
    videos: int
    spearman: float
    typical_miss: float
    agent: str
    fitted_on: str

    def views_per_follower(self, mean_stage: float) -> float:
        return 10 ** (self.intercept + self.slope * mean_stage)

    def expected_views(self, mean_stage: float, followers: int) -> float:
        return followers * self.views_per_follower(mean_stage)


def calibrate(points: list[Point], agent: str) -> CalibrationModel:
    if len(points) < MIN_VIDEOS:
        raise ValueError(f"Calibration needs at least {MIN_VIDEOS} real videos; you gave {len(points)}.")
    xs, ys = [p.mean_stage for p in points], [p.log_ratio for p in points]
    intercept, slope = fit_line(xs, ys)
    return CalibrationModel(intercept, slope, len(points), spearman(xs, ys), leave_one_out_miss(points),
                            agent, date.today().isoformat())


def save_model(model: CalibrationModel, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(model), indent=2) + "\n")


def load_model(path: Path = MODEL_PATH) -> CalibrationModel | None:
    return CalibrationModel(**json.loads(path.read_text())) if path.exists() else None
