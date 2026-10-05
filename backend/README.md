# Viralyst backend

The Python simulation engine. Run every command from this folder.

```bash
uv run run.py examples/good_demo.json            # one simulation, full report
uv run run.py examples/good_demo.json --seed 7   # repeat an exact run
uv run run.py examples/weak_demo.json --runs 200 # how often each outcome happens
uv run run.py examples/good_demo.json --agent ai # AI personas (shows the cost and asks first)
uv run pytest                                    # run the tests
uv run scripts/readme_images.py                  # redraw the README images
```

## What's where

| Path | What it does |
|---|---|
| `run.py` | Command-line entry point |
| `viralyst/models.py` | Data shapes: VideoBrief, Persona, Reaction, Wave |
| `viralyst/personas.py` | Generates crowds of in-target and out-of-target personas |
| `viralyst/agent.py` | Rule-based persona: formulas and dice rolls (free) |
| `viralyst/llm_agent.py` | AI persona: Claude decides and writes comments |
| `viralyst/algorithm.py` | Scores a wave against a typical reel |
| `viralyst/simulation.py` | The cascade: wave → score → push or stop |
| `viralyst/report.py` | Prints the results |
| `examples/` | Sample video briefs with a target audience |
| `tests/` | Automated tests (pytest) |
| `scripts/` | Developer helpers |
| `.env.example` | Template for your Claude API key (copy to `.env`) |
