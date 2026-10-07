# Lesson 3: Realistic personas

Until now a persona was a name, an age and three tags. That's enough for formulas, but an AI
persona needs a *life* to role-play. In this phase people got jobs, cities, a short bio and a
"moment". The audience can now be described in plain English and turned into people by Claude.

```bash
cd backend
uv run run.py examples/good_demo.json                     # now uses examples/indie_founders.audience.json
uv run run.py examples/good_demo.json --audience my.audience.json
uv run build_audience.py "who your video is for" --out examples/mine.audience.json   # needs a key
```

## Map of the new code

| File | What it does |
|---|---|
| `viralyst/data/everyone_else.json` | 24 everyday Instagram users who are *not* your audience |
| `examples/indie_founders.audience.json` | The examples' audience: description, tags, ages and 12 archetypes |
| `viralyst/personas.py` | Builds each person from an archetype, with small random differences |
| `viralyst/audience_builder.py` | Asks Claude to turn a description into archetypes, then checks the answer |
| `build_audience.py` | Command-line tool for the audience builder |
| `viralyst/loading.py` | Reads and writes the JSON files (moved here from three places) |
| `viralyst/claude.py` | Shared Claude helpers: prices, cost counting, fallbacks (moved out of `llm_agent.py`) |

## Concept 1: Archetypes with variation

An **archetype** is a template, like "bootstrapped SaaS founder, 31, Austin, allergic to fluff".
For each viewer we pick an archetype at random and `nudge` it:

- age ± 4 years (kept inside the audience's range)
- pickiness ± 0.15, sharing ± 0.1
- attention span 70–130% of the template
- a new name and a random **moment**

So 450 viewers come from about 36 templates, but no two are identical. This balances two risks:
fully random people are unrealistic ("a 16-year-old SaaS founder who loves parenting"), while
identical copies all behave the same, which an AI simulation must avoid. When every persona thinks
alike, the result is called a **monoculture**.

## Concept 2: Context changes behavior

The same person reacts differently "in bed, about to sleep" than "procrastinating at work". The
`moment` costs nothing and makes AI personas more varied and more realistic. The rules agent
ignores it, because formulas can't use a sentence.

## Concept 3: Data is not code

People live in **JSON files**, not in Python. That means:

- anyone can add or edit a persona without touching code,
- the same code works for any audience, so you just point it at a different file,
- `--audience` lets you test one video on many audiences: an A/B test of *who*, not *what*.

Rule of thumb: if it's something you'd *configure* (who, what, how many), make it data. If it's
*logic* (how to decide, how to score), make it code.

## Concept 4: Generate once, use many times

The audience builder calls Claude **once**, for about $0.07, and saves the result. Every simulation
then reuses the file for free. Compare that with AI personas, which call Claude once *per viewer per
run*. Asking "how often does this run?" before choosing where to use an AI model is one of the most
important cost habits.

## Concept 5: Never trust model output blindly

Structured outputs guarantee the *shape* of the answer (an `int` is an int), not that it's
*sensible*. So `clean()` in `audience_builder.py` checks everything:

- **Controlled vocabulary:** interest tags must come from `GENERAL_INTERESTS`. A tag like "AI tools"
  would never match a video tagged "ai", so unknown tags are dropped.
- **Clamping:** pickiness is forced into 0–1, ages into the audience range, attention into 3–60 seconds.
- **Invariants** (rules that must always hold): every audience member shares at least one audience interest.
- **Fail loudly:** with no valid tags at all, it raises an error instead of saving a broken file.

The tests in `tests/test_audience_builder.py` feed it deliberately bad answers to prove each check works.

## Concept 6: Refactoring with a safety net

Loading JSON was written three times (in `run.py`, the tests and the image script), and the Claude
helpers were about to be needed in two places. So they moved into `loading.py` and `claude.py`. This
is **refactoring**: changing the structure without changing the behavior.

How do we know nothing broke? The 31 tests from before still pass, untouched. That's the real payoff
of tests: they let you reorganize code without fear.

## Concept 7: Your model, your assumptions

The good demo used to be "strong or viral" 84% of the time. Now it's 64%. The video didn't change,
the *audience model* did. Before, every target-audience person had two of the audience's three
interests. Now they're realistic: a freelance designer cares about design and productivity, but not
AI. Fewer people are a perfect match, so it's harder to break out.

Every simulation is built on assumptions like this. Being able to say *which* assumption moved the
result is what makes a simulation trustworthy.

> **Update from Lesson 6:** part of that drop had a second cause. The "typical reel" yardstick was still
> the one measured in Phase 1, before audiences became realistic, so it was too strict. Re-measuring it
> put the good demo at 93% strong-or-viral. Both effects were real, and only measuring separated them.

## Python you used in this phase

- **`field(default_factory=list)`:** a dataclass default that's a list must be made fresh for each object.
  A plain `= []` would make every Audience share one list, a classic Python trap.
- **`a or b`:** use `a` unless it's empty, otherwise `b` (the outsider fallback in `personas.py`).
- **`{**data, "archetypes": archetypes}`:** copy a dict and replace one key.
- **`isinstance(audience, str)`:** checks the type of a value (is the audience a file name or written out?).
- **`dataclasses.asdict(...)`:** turns a dataclass, including nested ones, into a dict ready for JSON.
- **`pytest.raises(ValueError)`:** a test that *passes* only if the code raises that error.

## Exercises

1. **Pickier founders.** In `indie_founders.audience.json`, raise every `pickiness` by 0.1. Predict,
   then run `--runs 200`. Undo with `git checkout -- examples/`.
2. **Wrong crowd.** Write `examples/gamers.audience.json` by hand with tags `["gaming", "memes"]` and
   ages 14–24, no archetypes. Run the good demo with `--audience examples/gamers.audience.json`. Why does it flop?
3. **Add yourself.** Add an archetype to `data/everyone_else.json` that describes you. Run the tests.
   Do they still pass?
4. **With a key:** `uv run build_audience.py "people who'd love your own product idea" --out examples/mine.audience.json`.
   Read the archetypes Claude made. Are they diverse? Would you change any?
5. **With a key:** run the good demo with `--agent ai --model claude-haiku-4-5` and read the
   "thinking" lines. Do the bios and moments come through in what people say?
