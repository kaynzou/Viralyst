# Viralyst

**Test your product demo video before you post it.**

Viralyst simulates an audience of personas, inside and outside your target market, and an
Instagram-style algorithm that decides how far your video spreads. Get the odds of it taking off,
see who engaged, and learn what to fix before you publish.

<p align="center">
  <img src="docs/images/how-it-works.svg" alt="A video brief goes to wave 1 (your followers). Each wave that scores at least 1.0 unlocks a bigger wave with more strangers, up to the broad Reels audience, and then a report." width="100%">
</p>

## How it works

1. **Describe the video:** its hook, quality, topics and length. Uploading the video itself is coming soon.
2. **Wave 1 reacts.** Each persona scrolls past, or watches, likes, comments, shares, saves or follows.
3. **The algorithm scores the wave** against a typical reel. Shares and watch time count most.
   Beat it and the video moves to a bigger, broader wave. Otherwise it stops.
4. **Read the report:** how far it got, which audiences engaged, and your weakest signal with a fix.

## Example

<p align="center">
  <img src="docs/images/report.svg" alt="Simulation report for a demo video: four waves, a STRONG verdict, a segment breakdown and engagement signals." width="100%">
</p>

One run is one possible future, so run it many times to see the odds:

<p align="center">
  <img src="docs/images/odds.svg" alt="Over 200 simulations, a weak demo flops 99% of the time while a strong demo is strong or viral 84% of the time." width="100%">
</p>

## Quick start

Requires [uv](https://docs.astral.sh/uv/). AI personas also need a [Claude API key](https://console.anthropic.com/settings/keys) in `backend/.env` (see `backend/.env.example`).

```bash
cd backend
uv run run.py examples/good_demo.json            # one simulation
uv run run.py examples/weak_demo.json --runs 200 # the odds
uv run run.py examples/good_demo.json --agent ai # AI personas played by Claude
uv run pytest                                    # run the tests
```

## Project structure

```
backend/    Python simulation engine, CLI and tests
frontend/   Web app (coming in Phase 5)
docs/       Step-by-step lessons and README images
```

## Roadmap

- [x] **Phase 1:** Simulation engine with rule-based agents
- [x] **Phase 2:** AI personas (Claude) that decide and write comments
- [ ] **Phase 3:** Persona generator from a plain-English audience description
- [ ] **Phase 4:** Video understanding (frames, transcript, vision model)
- [ ] **Phase 5:** API and web app with a live view of the cascade
- [ ] **Phase 6:** Calibration against real results, A/B testing
- [ ] **Phase 7:** Deploy
