# Lesson 7: Going online

Until now Viralyst ran only on your Mac. This phase made it safe and ready to run on the internet,
where anyone can visit, including people who might try to spend your money.

The step-by-step guide is in [`deploy/README.md`](../../deploy/README.md). This lesson explains the
ideas behind it.

## Map of the new code

| File | What it does |
|---|---|
| `backend/viralyst/settings.py` | Online settings from environment variables: allowed websites, access code, daily budget |
| `backend/Dockerfile` | The recipe for the API's container |
| `backend/.dockerignore` | Files that must never go into the container |
| `.github/workflows/deploy-api.yml` | Sends the backend to Hugging Face on every push |
| `deploy/huggingface/README.md` | The Space's settings (Hugging Face reads them from this README) |
| `deploy/README.md` | The deployment guide |
| `frontend/components/AccessCode.tsx` | The unlock box on the website |
| `frontend/lib/api.ts` | Now sends the access code and streams with `fetch` |
| `backend/tests/test_deploy.py` | 10 tests that pretend to be the live server |

## Concept 1: Same code, different settings

The code on your laptop and on the server is identical. What differs is a handful of **environment
variables**, settings handed to a program when it starts:

| Variable | Where | Locally | Online |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | API | in `backend/.env` | a Space **secret** |
| `VIRALYST_ACCESS_CODE` | API | not set, so AI is open | a Space **secret** |
| `VIRALYST_DAILY_BUDGET` | API | not set, so no cap | a Space variable |
| `VIRALYST_ALLOWED_ORIGINS` | API | not set, so localhost only | your Vercel address |
| `NEXT_PUBLIC_API_URL` | website | defaults to localhost:8000 | your Space address |

One subtlety: `NEXT_PUBLIC_…` variables are **baked into the website when it's built**, because they end
up in JavaScript that runs in visitors' browsers. So change one, and you must redeploy. That's also why
a secret must never have a `NEXT_PUBLIC_` name: everyone could read it.

## Concept 2: Secrets live outside git

Your key and access code are never in the code or in git. Each service has a vault for them:
GitHub **Secrets** (for the Action), Hugging Face **Secrets** (for the API), Vercel **Environment Variables**.
A secret is hidden even from people who can read your public code. A *variable* is for settings that
aren't secret, like the daily budget.

## Concept 3: Containers

A **container** packages the program with everything it needs: the right Python, ffmpeg, every
library, even the Whisper model. It then runs identically on any server. The `Dockerfile` is its recipe,
read from top to bottom:

1. `FROM`: start from a small Linux that already has Python 3.12 and uv.
2. `RUN apt-get install ffmpeg`: add the video tool.
3. `useradd` / `USER user`: run as an ordinary user, never as `root`, so a bug can't take over the machine.
4. `COPY pyproject.toml uv.lock` then `uv sync`: install the libraries *before* copying the code. Docker
   saves each step as a **layer** and reuses it if nothing above it changed, so editing code doesn't
   reinstall everything.
5. `RUN python -c "...WhisperModel(...)"`: download the speech model at build time, not on the first upload.
6. `CMD fastapi run ...`: the command that starts the API.

Your Mac doesn't have Docker, so I **rehearsed** each step instead: assembled the Space folder the way the
Action does, installed with Python 3.12 and no dev tools, started the API with the production command,
and tested it with `curl`.

## Concept 4: Automatic deployment (CI/CD)

A **GitHub Action** is a script GitHub runs on its own computers when something happens. Ours
(`deploy-api.yml`) runs when you push changes to `backend/`:

1. It checks out your code.
2. It builds a folder containing `backend/` plus the Space's settings README.
3. It pushes that folder to your Space, which builds the container.

It skips itself (`if: vars.HF_SPACE != ''`) until you've configured it, so it can't fail before then.
Vercel does the same for the website without any file: it watches your repo. Push once, and both update.
This is **CI/CD** (continuous integration / continuous deployment).

## Concept 5: Protecting your money (defense in depth)

A public address plus your API key means anyone could run AI personas on your bill. No single lock is
perfect, so there are several, each covering what the others miss:

1. **The access code.**
   - It's sent in a **header** (`X-Viralyst-Code`), not the address, because addresses end up in browser
     history, server logs and shared links.
   - It's compared with `hmac.compare_digest`, which takes the same time however many letters are right,
     so it can't be guessed one letter at a time by timing.
   - A wrong code costs the guesser a 1-second wait.
2. **The daily budget.** Before an AI run starts, the server checks that today's spending *plus the
   most this run could cost* stays under the budget. Afterwards it records what was really spent. It
   lives in memory, so a restart resets it.
3. **The Anthropic Console spend limit.** The final backstop, outside your code entirely.

**CORS is not one of these locks.** CORS stops *other websites* from using visitors' browsers to call your
API. But `curl` or a script ignores CORS completely. That's exactly why the access code exists: it
protects against everyone, not just browsers.

## Concept 6: Streaming with `fetch` instead of `EventSource`

`EventSource` (Lesson 5) can't send headers, so it couldn't send the access code. The website now
streams with `fetch`: it reads the response piece by piece and splits it into events at each blank line.
A bonus: when the server refuses ("budget used up"), the page now shows the server's actual message.

## Concept 7: Free tiers have trade-offs

- **Sleeping:** an unused Space goes to sleep, so the first visitor waits for it to wake up.
- **Temporary disk:** uploads disappear on restart. A real product would use a storage service and a database.
- **Fair use:** free plans are for personal projects. A business would pay for guaranteed resources.

## Python and TypeScript you used in this phase

- **`os.environ.get(...)`:** read a setting from the environment, with a default when it isn't set.
- **`hmac.compare_digest`:** compare secrets safely.
- **`Header(None, alias="X-Viralyst-Code")`:** FastAPI reads a request header into a parameter.
- **`try` / `finally`:** the budget records the real cost even when a run fails halfway.
- **`AbortController`:** stops a `fetch` stream when you start another run or leave the page.
- **`localStorage`:** remembers the access code in your browser, inside `try`, because private windows can block it.

## Exercises

1. **Read the Dockerfile** and explain each line in your own words.
2. **Make your access code** (the command is in `deploy/README.md`) and save it in a password manager.
3. **Deploy!** Follow `deploy/README.md` step by step.
4. **Test the lock from the outside.** Run `curl https://<your-space>.hf.space/api/status`. Is AI locked?
   Then add `-H "X-Viralyst-Code: <your code>"` and run it again.
5. **See CORS in action.** Open any other website, open the browser console (Cmd+Option+J), and run
   `fetch("https://<your-space>.hf.space/api/status")`. It's blocked. The same request with `curl` works.
   Why is that fine?
