# Lesson 2: AI personas

In Lesson 1 every viewer was a formula. Now each viewer can be played by Claude: it reads who the
person is and what the reel shows, decides what they do, and writes their first impression and
their comment. The simulation, the algorithm and the report didn't need to change. That's the
"slot" from Lesson 1 paying off.

```bash
cd backend
uv run run.py examples/good_demo.json --agent ai              # asks before spending anything
uv run run.py examples/good_demo.json --agent ai --model claude-haiku-4-5
```

## Map of the new code

| File | What it does |
|---|---|
| `viralyst/llm_agent.py` | The AI persona: prompt, request to Claude, cost tracking, saved answers |
| `viralyst/agent.py` | Gained `react_wave()`, so both agents look the same to the simulation |
| `run.py` | New flags: `--agent`, `--model`, `--yes`, `--fresh`, `--workers` |
| `tests/test_llm_agent.py` | Tests that use a fake Claude: free, instant, no key needed |
| `.env.example` | Template for your secret API key |

## Concept 1: A persona is a prompt

A language model doesn't "become" Priya. We describe Priya and the situation, and ask what she does.
Every request has two parts:

- **System prompt** (same for everyone): how people really behave on Reels, plus the video.
- **User message** (different per person): who this person is.

Read `INSTRUCTIONS` in `llm_agent.py`. Most of it fights one problem: **language models are too nice.**
Ask one if it would like a product video and it says yes. So the prompt reminds it that most reels
get swiped in a second, gives real-world base rates ("likes about 1 in 15"), and says "you are not
the creator's friend". Writing these instructions is called **prompt engineering**, and it's most of
the craft in AI products.

We also **never tell a persona whether it's in the target audience.** It only sees its interests and
has to work out whether it cares. Telling it would leak the answer.

## Concept 2: Structured outputs

We need booleans and numbers, not an essay. `Decision` is a **Pydantic model**: a class that
describes the exact shape of the answer:

```python
class Decision(BaseModel):
    first_impression: str
    keeps_watching: bool
    seconds_watched: int
    ...
```

We pass it as `output_format=Decision`, and the API guarantees the answer matches that shape.
We get back a real Python object, `response.parsed_output.liked`, with no text parsing.

**Field order matters.** The model writes fields in order, so it writes `first_impression` *before*
deciding `keeps_watching`. Writing the reaction first makes the decision more grounded.

## Concept 3: Tokens and money

Models read and write **tokens**, chunks of about 4 characters. You pay per million tokens, and
writing (output) costs more than reading (input):

| Model | Input | Output | Good for |
|---|---|---|---|
| `claude-opus-5-5` | $4 | $20 | Best judgment (default) |
| `claude-sonnet-5-5` | $2 | $10 | Balanced |
| `claude-haiku-4-5` | $1 | $5 | Cheapest, fastest |

Opus and Sonnet also **think** briefly before answering, and thinking is billed as output. We set
`effort: "low"` because a scroll decision is quick, not a math problem.

Every response reports its `usage` (tokens in and out), and the `Usage` class adds it up. After an AI
run you see the real cost, not a guess.

## Concept 4: Prompt caching

All 450 personas share the same ~750-token system prompt. **Prompt caching** lets Claude store that
shared beginning. Later requests that start with the exact same text read it from the cache at about
5% of the normal price. We mark it with `cache_control`, and in `react_wave` we ask **one** persona
first, so the cache exists before the other 449 arrive.

The rule: the cached part must be **byte-for-byte identical** and come **first**. That's why the
video lives in the system prompt (shared), and the persona comes after it (varies).
Haiku 4.5 needs at least 4,096 tokens to cache, so with our prompt only Opus and Sonnet benefit.

## Concept 5: Doing many things at once (threads)

One request takes a few seconds, so 450 in a row would take half an hour. A `ThreadPoolExecutor`
runs up to 8 (`--workers`) at the same time:

```python
with ThreadPoolExecutor(max_workers=self.workers) as pool:
    rest = list(pool.map(lambda persona: self.react(persona, video), crowd[1:]))
```

When threads share data, two can update a counter at the same instant and lose a count. The
`threading.Lock` in `Usage` makes them take turns.

## Concept 6: Things go wrong, so plan for it

- **Rate limits (429) and busy servers (5xx):** the SDK automatically waits and retries (we allow 6
  retries). If a person still fails, we skip them and count it. One missing viewer doesn't break a wave.
- **Refusals:** a safety check can decline a request (`stop_reason == "refusal"`). With
  `fallbacks: "default"`, Anthropic retries on another model for us. If it still fails, we skip that person.
- **A wrong or missing key:** a clear message instead of a crash.

## Concept 7: Don't pay twice (saved answers)

Every answer is saved in `backend/.cache/decisions/`. The file name is a **hash** of the model plus the
exact prompt, a short fingerprint like `3f9a…`. The same persona and the same video give the same
fingerprint, so the saved answer is reused for free. Rerunning `--seed 7` costs nothing the second
time and gives exactly the same report. Use `--fresh` to ask Claude again.

## Concept 8: Secrets

Your API key is like a password linked to your credit card.

- It lives in `backend/.env`, which `.gitignore` excludes, so it can never be committed or pushed.
- `load_dotenv()` in `run.py` copies it into the environment, where the SDK finds it.
- Never paste it into chat, code, or screenshots. If it leaks, delete it in the Console and make a new one.

## Concept 9: Testing code that costs money

`tests/test_llm_agent.py` swaps the real client for `FakeClaude`, a tiny class with the same
`beta.messages.parse(...)` method that returns a canned answer and records each request. The tests
check our logic (prompt contents, cost math, error handling, saved answers) for free in milliseconds.
Passing a fake in place of a real dependency is called **dependency injection**: `LLMAgent(client=...)`.

## Python you used in this phase

- **Pydantic `BaseModel`:** classes that validate data. `Decision.model_validate_json(text)` rebuilds one from JSON.
- **`try` / `except`:** catch specific errors and decide what to do instead of crashing.
- **`**model_options(...)`:** unpacks a dict into keyword arguments, so `f(**{"a": 1})` is `f(a=1)`.
- **`str | None`:** "a string, or nothing". The function may return no answer.
- **`hashlib.sha256(...).hexdigest()`:** a fingerprint of some text.
- **`pathlib.Path`:** file paths that work on every operating system (`folder / "file.json"`).

## Exercises

Exercise 1 is free. The rest spend a little money, so read the cost prompt each time.

1. **Read the prompt.** Open `llm_agent.py`. Which lines in `INSTRUCTIONS` push against "too nice"?
   What would you add?
2. **First AI run.** `uv run run.py examples/weak_demo.json --agent ai --model claude-haiku-4-5`.
   It's cheap because the weak demo usually stops after 30 people. Read the first impressions.
   Do they sound like real people?
3. **Rules vs AI, same people.** Run the good demo with `--seed 7` in both modes. The followers are
   identical (same seed). Where do the formulas and Claude disagree?
4. **Run it again.** Repeat the exact same AI command. It's instant and free. Why?
5. **Model shoot-out.** Same seed, three models. Do they agree? Is Opus worth 5x Haiku *for this job*?

## What isn't solved yet

- **The benchmarks were tuned for the rules agent.** The "typical reel = 1.0" numbers came from
  formula people. AI personas may like, share or comment at different rates, so scores in AI mode
  aren't comparable yet. Re-measuring benchmarks for AI personas is part of calibration (Phase 6).
- **AI personas may still be too generous.** We'll find out by reading their answers.
- **Personas are thin:** a name, an age and three interests. Phase 3 gives them real backstories.
