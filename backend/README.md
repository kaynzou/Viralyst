# Viralyst backend

The Python simulation engine. Run every command from this folder.

```bash
uv run run.py examples/good_demo.json            # one simulation, full report
uv run run.py examples/good_demo.json --seed 7   # repeat an exact run
uv run run.py examples/weak_demo.json --runs 200 # how often each outcome happens
uv run run.py examples/good_demo.json --agent ai # AI personas (shows the cost and asks first)
uv run run.py examples/good_demo.json --audience examples/other.audience.json
uv run build_audience.py "who it's for" --out examples/mine.audience.json
uv run pytest                                    # run the tests
uv run scripts/readme_images.py                  # redraw the README images
```

## What's where

| Path | What it does |
|---|---|
| `run.py` | Command-line entry point: run a simulation |
| `build_audience.py` | Command-line entry point: create an audience file with Claude |
| `viralyst/models.py` | Data shapes: VideoBrief, Audience, Archetype, Persona, Reaction, Wave |
| `viralyst/personas.py` | Builds crowds of people from archetypes, with small random differences |
| `viralyst/audience_builder.py` | Turns a plain-English audience description into archetypes |
| `viralyst/agent.py` | Rule-based persona: formulas and dice rolls (free) |
| `viralyst/llm_agent.py` | AI persona: Claude decides and writes comments |
| `viralyst/algorithm.py` | Scores a wave against a typical reel |
| `viralyst/simulation.py` | The cascade: wave → score → push or stop |
| `viralyst/report.py` | Prints the results |
| `viralyst/claude.py` | Shared Claude helpers: models, prices, cost tracking |
| `viralyst/loading.py` | Reads and writes video and audience JSON files |
| `viralyst/data/` | Everyday Instagram users outside your audience |
| `examples/` | Sample videos and the audience they're aimed at |
| `tests/` | Automated tests (pytest) |
| `scripts/` | Developer helpers |
| `.env.example` | Template for your Claude API key (copy to `.env`) |
