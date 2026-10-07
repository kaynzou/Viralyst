# Viralyst backend

The Python simulation engine. Run every command from this folder.

```bash
uv run fastapi dev viralyst/api.py                # the web API on http://localhost:8000 (/docs to explore)
uv run run.py examples/good_demo.json            # one simulation, full report
uv run run.py examples/good_demo.json --seed 7   # repeat an exact run
uv run run.py examples/weak_demo.json --runs 200 # how often each outcome happens
uv run run.py examples/good_demo.json --agent ai # AI personas (shows the cost and asks first)
uv run run.py examples/good_demo.json --audience examples/other.audience.json
uv run build_audience.py "who it's for" --out examples/mine.audience.json
uv run analyze_video.py examples/sample_demo.mp4 --out examples/sample_demo.json --voiceover
uv run scripts/make_sample_video.py              # redraw the sample video (macOS)
uv run scripts/readme_demo.py                    # redraw the Phase 4 demo GIF
uv run compare.py examples/weak_demo.json examples/good_demo.json   # A/B test
uv run measure_benchmarks.py --agent rules       # re-measure the "typical reel" (free)
uv run calibrate.py calibration/results.csv      # check predictions against real results
uv run pytest                                    # run the tests
uv run scripts/readme_images.py                  # redraw the README images
```

## What's where

| Path | What it does |
|---|---|
| `run.py` | Command-line entry point: run a simulation |
| `build_audience.py` | Command-line entry point: create an audience file with Claude |
| `analyze_video.py` | Command-line entry point: turn a video file into a video brief |
| `compare.py` | Command-line entry point: A/B test two or more versions of a video |
| `measure_benchmarks.py` | Command-line entry point: measure the "typical reel" for a kind of persona |
| `calibrate.py` | Command-line entry point: compare predictions with your real Instagram results |
| `viralyst/models.py` | Data shapes: VideoBrief, Audience, Archetype, Persona, Reaction, Wave |
| `viralyst/personas.py` | Builds crowds of people from archetypes, with small random differences |
| `viralyst/audience_builder.py` | Turns a plain-English audience description into archetypes |
| `viralyst/agent.py` | Rule-based persona: formulas and dice rolls (free) |
| `viralyst/llm_agent.py` | AI persona: Claude decides and writes comments |
| `viralyst/algorithm.py` | Scores a wave against a typical reel |
| `viralyst/simulation.py` | The cascade: wave → score → push or stop, one wave at a time |
| `viralyst/summary.py` | What a simulation means, as data: verdict, reach, signals, odds |
| `viralyst/report.py` | Prints the results in the terminal |
| `viralyst/api.py` | The web API the website uses (FastAPI), with live streaming |
| `viralyst/pipeline.py` | Video file → frames + transcript → saved brief (used by the CLI and the API) |
| `viralyst/media.py` | ffmpeg helpers: video facts, frames, audio |
| `viralyst/speech.py` | Speech-to-text with Whisper (runs locally) |
| `viralyst/video_analyzer.py` | Claude looks at frames and transcript and writes the video brief |
| `viralyst/voiceover.py` | Text-to-speech with Supertonic (runs locally) |
| `viralyst/experiments.py` | A/B tests: breakout rates, 95% ranges, "too close to call" |
| `viralyst/benchmarks.py` | Measures and stores "typical reel" benchmarks per model |
| `viralyst/calibration.py` | Fits simulated stages to real views: rank correlation, line, leave-one-out check |
| `viralyst/claude.py` | Shared Claude helpers: models, prices, cost tracking |
| `viralyst/loading.py` | Reads and writes video and audience JSON files |
| `viralyst/data/` | Everyday Instagram users outside your audience |
| `examples/` | Sample video briefs, a sample video file and the audience they're aimed at |
| `calibration/` | Your real results, the fitted model and measured benchmarks (see its README) |
| `tests/` | Automated tests (pytest) |
| `scripts/` | Developer helpers |
| `.env.example` | Template for your Claude API key (copy to `.env`) |
