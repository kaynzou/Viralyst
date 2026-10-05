# Viralyst

Upload a product demo video and see how it might spread on Instagram before you post it.

Viralyst builds a crowd of simulated people, some in your target audience and some outside it,
and has them react to your video: scroll past, watch, like, comment, share, save, follow.
A simplified Instagram-style algorithm scores each wave of viewers and decides whether to push
the video to a bigger, broader audience, just as Reels distribution works.

## Run it

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv run run.py examples/good_demo.json            # one simulation, full report
uv run run.py examples/good_demo.json --seed 7   # repeatable run
uv run run.py examples/weak_demo.json --runs 200 # how often each outcome happens
```

## Roadmap

- [x] **Phase 1: Simulation engine** with rule-based agents ([lesson](docs/learn/01-simulation-engine.md))
- [ ] **Phase 2: LLM agents.** Personas decide and write comments with an LLM
- [ ] **Phase 3: Persona generator.** Describe your audience in words, get a diverse crowd
- [ ] **Phase 4: Video understanding.** ffmpeg + transcript + vision model produce the video brief
- [ ] **Phase 5: API + web UI.** Upload, watch the cascade live, read the report
- [ ] **Phase 6: Calibration + A/B.** Compare against real results and between video versions
- [ ] **Phase 7: Deploy and launch**
