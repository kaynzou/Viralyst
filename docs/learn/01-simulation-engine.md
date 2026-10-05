# Lesson 1: The simulation engine

In this phase there is no AI and no video yet. We built the heart of Viralyst:
a fake audience reacts to a described video, and a fake "Instagram algorithm"
decides whether to keep spreading it. Every later phase plugs into this.

## Map of the code

Read the files in this order. Each one holds one idea.

| File | Idea | Plain English |
|---|---|---|
| `viralyst/models.py` | Data shapes | "What is a Persona? A Reaction? A Wave?" |
| `viralyst/personas.py` | The crowd | Makes random people, some in your target audience, some not |
| `viralyst/agent.py` | One person's brain | Given a person and a video: scroll, watch, like, share...? |
| `viralyst/algorithm.py` | The judge | Turns a wave's reactions into one score |
| `viralyst/simulation.py` | The loop | Wave 1 → score → push or stop → Wave 2 → ... |
| `viralyst/report.py` | The output | Prints results a human can read |
| `run.py` | The entry point | Reads your JSON file and starts everything |

## Concept 1: Agent-based simulation

An **agent-based simulation** has three parts:

1. **Agents.** Individuals with their own traits (our `Persona`: age, interests, pickiness...).
2. **Rules.** How each agent behaves (our `MockAgent.react`).
3. **An environment that runs in steps.** Here that's the waves, and the algorithm between them.

You never write "the video goes viral" anywhere. You only write how *one person* behaves
and how *the algorithm* judges a group. Virality **emerges** from many small decisions.
That's the whole point of the project.

## Concept 2: Randomness and seeds

Real people are unpredictable, so the agent rolls dice: `rng.random() < 0.3` is true
about 30% of the time.

Computers can't really roll dice. `random.Random(seed)` makes a *pseudo-random* sequence
that looks random but is fully decided by the **seed** number. Same seed, same sequence,
same result. That's why `--seed 7` always gives the same report.

Bonus: with the same seed, two different videos get shown to **the exact same followers**
in wave 1. That's a fair A/B test.

## Concept 3: The score (how the "algorithm" judges a wave)

For each wave we compute **rates**, for example `share rate = people who shared / viewers`.

Then we compare each rate with a **benchmark**: what a typical reel gets.
`strength = rate / benchmark`, so 1.0 means typical and 2.0 means twice as good.
This is called **normalizing**. Without it, likes (around 10%) would always look more
important than shares (around 1.6%), even though shares matter more.

Finally a **weighted sum**:

```
score = 0.30*watch + 0.25*share + 0.15*save + 0.10*comment + 0.10*like + 0.10*follow
```

The weights add up to 1.0, so a perfectly typical video scores exactly 1.0. Shares and
watch time get the biggest weights because Instagram has publicly said those matter most
for reaching new people.

Each strength is **capped at 3x** so one lucky share in a 30-person wave can't carry a bad video.

## Concept 4: The cascade

```
Wave 1  your followers         30 people   90% in target
Wave 2  similar non-followers  60 people   60% in target
Wave 3  Explore / Reels tab   120 people   35% in target
Wave 4  broad Reels audience  240 people   15% in target
```

Each wave has to score at least 1.0 (`PUSH_THRESHOLD`) to unlock the next one. Later waves
contain more strangers, who care less about your topic, so it gets harder to keep spreading.
A video only goes far if it works on people who *weren't* looking for it, which is exactly
how real virality works.

## Concept 5: Monte Carlo (one run is one possible future)

Run the same video twice without a seed and you can get different verdicts. That isn't a bug.
Small waves are noisy, like flipping a coin 10 times.

The fix is to run the simulation many times and count the outcomes:

```bash
uv run run.py examples/good_demo.json --runs 200
```

"Strong or viral 84% of the time" is a far more honest answer than a single "VIRAL!".
Repeating a random simulation many times is called the **Monte Carlo method**.

## Concept 6: Why fake agents first

`MockAgent` is a stand-in. The simulation only ever calls
`agent.react(persona, video, rng)` and gets back a `Reaction`. In Phase 2 we write an
`LLMAgent` with the **same `react` method**, and nothing else has to change.
Designing a "slot" so parts can be swapped is one of the most useful habits in programming.

Fake agents also cost nothing and run in milliseconds, so we could tune the engine by
running 500 simulations in a second. With LLM agents, every run costs money.

## Python you used in this phase

- **Modules and packages.** Each `.py` file is a module. The `viralyst/` folder with
  `__init__.py` is a package. `from .models import Persona` means "from models.py in this
  same package".
- **`@dataclass`.** Writes the boring `__init__` code for you. `Persona(name="ben", age=30, ...)`.
- **Type hints.** `def score(rates: dict[str, float]) -> float:` says what goes in and what
  comes out. Python doesn't enforce them, but they make code readable.
- **f-strings.** `f"{0.4567:.0%}"` gives `46%`, and `f"{555500:,}"` gives `555,500`.
- **List comprehensions.** `[agent.react(p, video, rng) for p in crowd]` is a loop that builds a list.
- **`sum()` on booleans.** `True` counts as 1, so `sum(r.liked for r in reactions)` counts the likes.
- **`argparse`.** Turns `--seed 7` on the command line into `args.seed == 7`.
- **`if __name__ == "__main__":`.** Runs `main()` only when you run this file directly.

## Tools

- **uv** manages Python versions, the virtual environment (`.venv/`) and packages.
  `uv run run.py ...` makes sure everything is set up, then runs the file.
- **git** tracks every version of your code. The project already has a repository.

## Exercises (try them, then predict before you run)

1. **Hook test.** In `examples/weak_demo.json`, change `hook_strength` from `0.2` to `0.8`.
   Before running, predict which outcome will become most common. Then run with `--runs 200`.
2. **What does Instagram value?** In `algorithm.py`, set the `share` weight to `0.05`
   and `like` to `0.30`. Does the good demo still go viral as often? Why?
3. **Tougher algorithm.** Change `PUSH_THRESHOLD` to `1.3`. How does the outcome chart change?
4. **Wrong audience.** In `good_demo.json`, change the audience interests to
   `["fitness", "cooking", "travel"]`. What happens and why?
5. **Your own product.** Copy `good_demo.json`, describe a video for something you'd build,
   and score it honestly from 0 to 1.

Undo your experiments afterwards with `git checkout -- .`, or just keep the ones you like.

## What isn't real yet

- The scores in the JSON (hook 0.85...) are made up by a human. **Phase 4** gets them from the actual video.
- The agent's brain is three formulas. **Phase 2** replaces it with an LLM that reads the
  persona and the video and decides like a person would, and writes real comments.
- "Rough reach" isn't calibrated against real Instagram data. **Phase 6** handles that.
