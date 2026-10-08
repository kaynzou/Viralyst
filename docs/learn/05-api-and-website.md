# Lesson 5: The API and the website

Viralyst now has a face. Start everything with one command from the project folder:

```bash
./dev.sh
```

Then open http://localhost:3000. Pick a video, press **Run simulation**, and watch the waves fill
with dots (one per simulated viewer). Click any dot to meet that person.

Two programs run at once:

```
Browser (localhost:3000)                     Python (localhost:8000)
Next.js website ──── HTTP requests ────────▶ FastAPI: viralyst/api.py
  React components ◀──── JSON / live events ── simulation, personas, Claude…
```

## Map of the new code

| Where | File | What it does |
|---|---|---|
| backend | `viralyst/api.py` | The API: endpoints the website calls |
| backend | `viralyst/summary.py` | Report data (verdict, signals…) shared by the terminal and the website |
| backend | `viralyst/pipeline.py` | Video analysis steps shared by `analyze_video.py` and the API |
| backend | `viralyst/simulation.py` | Now a *generator*: hands back each wave as soon as it's done |
| backend | `tests/test_api.py` | 9 API tests, including upload → analyze → simulate with a fake Claude |
| frontend | `app/`, `components/`, `lib/` | The website (see `frontend/README.md` for each file) |
| root | `dev.sh` | Starts both programs together |

## Concept 1: Client and server

- The **server** (Python) has the data and does the work. The **client** (the browser) shows it and
  reacts to clicks.
- They talk over **HTTP**: the browser sends a request like `GET /api/examples`, and the server answers
  with **JSON**, which is text in the same shape as Python dicts and lists.
- Each program listens on its own **port**: 8000 for the API, 3000 for the website.

Why split them? The API key and the heavy work (Whisper, ffmpeg, Claude) stay on the server. A browser
can never see the key, because it never leaves Python.

## Concept 2: An API is a menu

| Endpoint | What it does |
|---|---|
| `GET /api/status` | Is the API up? Is an API key set? Is ffmpeg installed? |
| `GET /api/examples` | The videos and audiences you can choose from |
| `GET /api/simulate` | Runs one simulation and **streams** it live |
| `GET /api/odds` | 200 free simulations: how often each outcome happens |
| `GET /api/estimate` | The most an AI run could cost, so the page can ask first |
| `POST /api/analyze` | Upload a video; get its brief and Claude's feedback |

FastAPI writes interactive documentation for you: open http://localhost:8000/docs while it's running,
click an endpoint, then **Try it out**.

## Concept 3: Live streaming (Server-Sent Events)

An AI run takes minutes. Instead of waiting for the end, the server sends events as they happen:

```
data: {"type": "start", "seed": 7, ...}
data: {"type": "wave", "number": 1, "score": 2.19, "reactions": [...]}
...
data: {"type": "done", "verdict": "VIRAL: ...", ...}
```

- **Python side:** `simulate()` uses `yield`, so it's a **generator** that hands back wave 1 before
  wave 2 exists. `StreamingResponse` sends each piece the moment it's yielded.
- **Browser side:** `EventSource` in `lib/api.ts` receives them one by one.
- **A gotcha:** when the stream ends, `EventSource` automatically *reconnects*, which would start a
  new simulation. So the page closes it itself when it sees `done` or `error`.

> **Update from Lesson 7:** the website now streams with `fetch` instead of `EventSource`, because
> `EventSource` can't send the access code header. The events are exactly the same.

The rules-based personas finish in milliseconds, so the page reveals waves one at a time on purpose
(a timer in `Simulator.tsx`). That way you can still watch the cascade.

## Concept 4: CORS, the browser's safety rule

By default a page from `localhost:3000` may not read answers from `localhost:8000`. That's a different
"origin", and browsers block it to protect you from malicious sites. The API explicitly allows the
website's address with `CORSMiddleware`.

## Concept 5: Never trust a request

Anyone who can reach a server can send it anything, so `api.py` defends itself:

- **An allow-list of files:** a video is chosen by id from a list the server built itself. A request for
  `../../.env` gets "404 not found" (there's a test that tries exactly that).
- **Uploads get a random name**, never the name the browser sent, and are size-limited.
- **Links never spend money:** a shared link can only start the free rules mode.
- **Validation for free:** `runs: int = Query(200, ge=10, le=1000)` makes FastAPI reject `runs=99999`.

## Concept 6: React in five ideas

1. **Components** are functions that return what to show: `Cascade`, `Report`, `PersonaCard`…
2. **Props** are their inputs: `<Report done={...} reactions={...} />`.
3. **State** (`useState`) is data that changes. When it changes, React redraws what depends on it.
4. **Effects** (`useEffect`) do things *after* drawing: load data when the page opens, run the
   timer that reveals waves, clean up when it closes.
5. **`"use client"`** marks components that run in the browser (clicks, state, live connections).
   `app/page.tsx` stays a Server Component that simply renders `Simulator`.

TypeScript types in `lib/types.ts` mirror the JSON from `api.py`. If one side changes, `tsc` points at
every place that needs updating.

## Concept 7: Styling with Tailwind and CSS variables

Tailwind classes describe style right on the element (`rounded-xl border p-4`). Colors are **CSS
variables** in `globals.css` (`--accent`, `--good`…), with different values for dark mode. That's
how the whole site switches themes without any extra code. People who turn off animations in their
system settings see the dots without the pop-in.

## Concept 8: The address bar as state (shareable links)

After a run, the address becomes `?video=examples/good_demo&audience=indie_founders&seed=7&run=1`.
Opening that link reproduces the exact same run, because the same seed means the same people and the
same dice rolls. `history.replaceState` updates the address without reloading the page.

## Concept 9: Working without an API key

`GET /api/status` reports whether a key is set, and the page greys out AI options with a note instead
of failing. `refresh_key()` re-reads `backend/.env` on each request, so the day you add your key the
AI features switch on by themselves. The page re-checks whenever you come back to the tab.

## Concept 10: Testing a web app

- **`TestClient`** calls the API in tests without starting a server.
- **Dependency overrides:** `app.dependency_overrides[claude_client] = FakeClaude` swaps the real Claude
  for a fake in one line. It's the same idea as Lesson 2, built into FastAPI.
- **Frontend checks:** `npx tsc --noEmit` (types), `npm run lint` (mistakes), `npm run build` (the real
  production build).
- **Looking at it:** I ran it in a browser in dark mode, light mode and on a phone-sized screen.

## Exercises

1. **Explore the API.** Open http://localhost:8000/docs, try `/api/odds` with `examples/weak_demo`, and
   read the JSON.
2. **Restyle it.** Change `--accent` in `frontend/app/globals.css`. The page updates as you save.
3. **Share a run.** Run the good demo, copy the address, and open it in a new tab. Same people?
4. **Data, not code.** Copy `backend/examples/good_demo.json` to `my_demo.json`, change the title and
   hook, and reload the page. It's in the list, without touching any code.
5. **With a key:** switch to AI personas, run it, and click dots to read real first impressions.

## What isn't done yet

- **It only runs on your computer.** Putting it online is Phase 7.
- **No accounts or database:** uploads are files in `backend/uploads/`.
- **AI runs report progress per wave,** not per person.
