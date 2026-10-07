# Calibration: checking Viralyst against reality

Simulations are only useful if they match what really happens. This folder holds your real results
and what Viralyst learns from them.

| File | What it is |
|---|---|
| `results.csv` | Your real videos and their real numbers (you fill this in) |
| `model.json` | What `calibrate.py` learned: how simulated stages turn into real views |
| `benchmarks.<model>.json` | The "typical reel" measured with AI personas (`measure_benchmarks.py`) |

## 1. Collect real results

For each reel you've already posted:

1. **Make a video brief** for it. With an API key:
   `uv run analyze_video.py my_reel.mp4 --out examples/my_reel.json`.
   Without one, copy `examples/good_demo.json` and describe the video by hand.
2. **Look up its numbers** in the Instagram app: open the reel → **View insights** → **Views**.
3. **Note your follower count** around the time you posted it.
4. **Add a row** to `results.csv` (paths are relative to the `backend/` folder):

```csv
video,followers,views
examples/my_reel.json,1200,3400
examples/launch_teaser.json,1250,980
```

Tips for numbers you can trust:
- Use reels that are **at least 7 days old**, since views keep growing for a few days.
- Use **one account**, so follower counts mean the same thing throughout.
- Aim for **10 or more videos**, ideally 20+. A mix of hits and misses teaches the most.

## 2. Run the calibration

```bash
cd backend
uv run calibrate.py calibration/results.csv
```

You get three answers:
- **Ranking check (Spearman, from −1 to +1):** do videos Viralyst rates higher really get more views?
  +0.7 or above is good.
- **Scale:** how many views per follower each stage means for your account.
- **Honest accuracy:** each video is predicted from a line fitted on the *other* videos, so the model
  can't cheat by memorising. "Within 2.0x" means a prediction of 4,000 views usually lands between
  2,000 and 8,000.

## 3. Use it

```bash
uv run run.py examples/good_demo.json --runs 200 --followers 1200
```

This prints the expected real views next to the odds. The website's odds panel shows it too.
