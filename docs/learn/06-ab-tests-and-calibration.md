# Lesson 6: Is it right? A/B tests, benchmarks and calibration

A simulator is only useful if it agrees with reality, and only honest if it admits when it doesn't
know. This phase added three tools for that:

```bash
cd backend
uv run compare.py examples/typical_reel.json examples/good_demo.json   # A/B test (free)
uv run measure_benchmarks.py --agent rules                             # check the yardstick (free)
uv run calibrate.py calibration/results.csv                            # compare with your real results
```

The website's new **A/B test** panel does the first one too.

## Map of the new code

| File | What it does |
|---|---|
| `viralyst/experiments.py` | Breakout rates, 95% ranges, comparing versions |
| `compare.py` | The A/B test command |
| `viralyst/benchmarks.py`, `measure_benchmarks.py` | Measure the "typical reel" for a kind of persona |
| `examples/typical_reel.json` | A deliberately ordinary video: the yardstick |
| `viralyst/calibration.py`, `calibrate.py` | Compare simulated stages with real views |
| `calibration/` | Your real results, the fitted model, AI benchmarks (instructions inside) |
| `frontend/components/ComparePanel.tsx` | The A/B panel on the website |

## Concept 1: Luck, and how many runs you need

One simulation is one possible future. Run the same video 200 times and count how often it
**breaks out** (reaches STRONG or VIRAL). That gives a rate, like "93%".

But 200 runs is still a sample, so the true rate could be a bit different. A **95% range**
(a *confidence interval*) says where it probably is: "93% (89%–96%)". `wilson_interval()` computes it.

- **More runs give a narrower range.** The width shrinks with the square root of the number of runs,
  so 4× more runs makes the range about 2× narrower.
- Wilson's formula stays sensible near 0% and 100%, where the simple "± 1.96 × standard error" would
  give impossible answers like −3%.

## Concept 2: A fair A/B test

To compare two versions you change **one thing** (the video) and keep everything else equal:

- **Same audience** for every version.
- **Same seeds**, so each version starts with exactly the same followers in wave 1.

Then compare the breakout rates: "B vs A: +91 points (95% range +86 to +94)".

- **The range excludes zero:** the difference is real. "B is better."
- **The range includes zero:** the difference could be luck. **"Too close to call."** Try two
  nearly identical versions and you'll see it. Refusing to name a winner is a feature, because a
  tool that always picks one would mislead you half the time.

**A bug worth remembering.** The first version used the simple formula for the difference
(difference ± 1.96 × standard error) and once printed "+87 to **+101** points", which is impossible,
since a difference of two percentages can't exceed 100. Near 0% and 100% that formula overshoots.
`compare()` now uses **Newcombe's method**, which builds the difference's range from the two Wilson
ranges and can never leave −100…+100. A test checks exactly that case.

## Concept 3: The yardstick was stale (a real finding)

Every score compares a wave with a **typical reel** (`BENCHMARKS` in `algorithm.py`). Those numbers
were measured in Phase 1. Then Phase 3 made audiences realistic, and nobody re-measured them.

When `measure_benchmarks.py` measured the typical reel (`examples/typical_reel.json`) with today's
personas, the real typical numbers came out lower: about 24% average watch, not 30%, and 7% likes,
not 10%. So since Phase 3, every video had been judged against a too-strict ruler.

After the update:

| | Before | After |
|---|---|---|
| Seed 7, wave 1 score | 2.19 | 2.39 |
| Good demo, strong or viral | 64% | 93% |
| Typical reel | (not measured) | mostly flop or niche, 3% strong |
| Weak demo | 99% flop | 99% flop |

In seed 7 the simulated people did *exactly* the same things (same likes, same shares). Only the
ruler changed. And a new test, `test_rules_benchmarks_in_the_code_are_up_to_date`, now fails if the
personas change without the benchmarks being re-measured, so this can't silently happen again.

## Concept 4: AI personas need their own yardstick

AI personas may like or share more or less often than the rules personas. If they were scored
against the rules' typical reel, an AI run would look better or worse just because the agent changed.

`uv run measure_benchmarks.py --agent ai --model claude-haiku-4-5` shows the typical reel to 300 AI
personas (it asks first; about $0.40 with Haiku) and saves the result to
`calibration/benchmarks.claude-haiku-4-5.json`. From then on, `LLMAgent` loads it and the simulation
scores AI runs against it automatically. Each model gets its own file, because each behaves differently.

## Concept 5: Calibration against reality

For videos you've really posted, you write down your followers and real views. Then `calibrate.py`:

1. **Simulates each video** many times and takes its *average stage* (1 = flop … 5 = viral).
2. **Puts views on a log scale.** Real views vary hugely (300 vs 300,000), so we use
   `log10(views ÷ followers)`, where each +1 means 10× more. Dividing by followers makes a big
   account and a small account comparable.
3. **Fits a straight line** (`fit_line`, "least squares") from average stage to log views per follower.
   That line is the scale: "stage 1 ≈ 0.4× your followers, stage 5 ≈ 11×" (example numbers).
4. **Checks the ranking** with **Spearman's rank correlation** (`spearman`), from −1 to +1. It only asks
   whether higher predictions go with more views, ignoring exact amounts. +0.7 or above is good.
5. **Measures honest accuracy** with **leave-one-out**. Each video is predicted from a line fitted on
   all the *other* videos, so the model can't cheat by having seen the answer. "Typically within 2.0×"
   means a prediction of 4,000 views usually lands between 2,000 and 8,000.

The fitted model is saved to `calibration/model.json`. After that,
`run.py ... --runs 200 --followers 1200` prints expected real views, and the website's odds panel shows
"about N× your follower count".

## Concept 6: Honest limits

- **A few videos give a rough guess.** Below 10, the command says so. 20+ is much better.
- **One account at a time:** the scale learned for your account won't fit someone with a different audience.
- **Correlation isn't proof.** A good ranking means the simulator is *useful*, not that it understands
  *why* videos spread.
- **Instagram changes,** so re-calibrate every few months.

## Python you used in this phase

- **`csv.DictReader`:** reads a spreadsheet file row by row, as dicts keyed by the header.
- **`statistics.mean` / `median`, `math.log10` / `sqrt`:** the building blocks of the formulas,
  written out in `calibration.py` so you can follow every step.
- **`nargs="+"`** in argparse: "one or more values", so `compare.py a.json b.json c.json` works.
- **`monkeypatch`** in tests: temporarily swaps something (like where benchmarks are saved) so tests
  never touch your real files.

## Exercises

1. **Too close to call.** Copy `examples/good_demo.json`, change `save_value` from 0.6 to 0.65, and
   compare the two. Then add `--runs 2000`. Does a winner appear? What does that tell you about tiny
   differences?
2. **Break the yardstick.** In `agent.py`, change the like chance from `0.05 + 0.5 * enjoyment` to
   `0.05 + 0.7 * enjoyment`. Run `uv run pytest`. Which test fails, and why? Re-measure with
   `measure_benchmarks.py --agent rules`, then undo your change.
3. **A/B on the website:** open the A/B panel and compare the three example videos in pairs.
4. **Your real results:** add five or more of your own reels to `calibration/results.csv`
   (instructions in `calibration/README.md`) and run `calibrate.py`. What's your rank correlation?
5. **With a key:** `uv run measure_benchmarks.py --agent ai --model claude-haiku-4-5`. Do AI personas
   engage more or less than the rules personas?

## What's next

Phase 7 puts Viralyst online, so other people can use it without installing anything.
