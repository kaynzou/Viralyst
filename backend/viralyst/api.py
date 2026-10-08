"""The web API: lets the website list examples, run simulations live, and analyze uploaded videos.

    cd backend
    uv run fastapi dev viralyst/api.py     # then open http://localhost:8000/docs to try every endpoint

Without an API key everything free still works; the AI endpoints answer with a clear
"add your key" message instead. A key added to backend/.env is picked up without a restart.
Online, settings.py adds an access code, a daily budget and the list of allowed websites.
"""

import json
import random
import shutil
import tempfile
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agent import MockAgent
from .calibration import load_model
from .claude import BAD_KEY, DEFAULT_MODEL, MISSING_KEY, PRICES, has_api_key
from .experiments import compare, run_arm
from .llm_agent import LLMAgent, estimate_cost
from .loading import load_audience, load_example
from .media import MissingFFmpeg, require_ffmpeg
from .models import Audience, Reaction, VideoBrief, WaveResult
from .pipeline import build_result, prepare, save_result
from .settings import CODE_HEADER, DailySpend, access_code_required, allowed_origins, code_is_valid, daily_budget
from .simulation import WAVES, run_cascade, simulate
from .speech import transcribe
from .summary import (STAGES, TIPS, all_reactions, furthest_stage, outcome_odds, reach, scroll_rate, segments,
                      signals, weakest)
from .video_analyzer import analyze

BACKEND = Path(__file__).resolve().parent.parent
EXAMPLES = BACKEND / "examples"
UPLOADS = BACKEND / "uploads"  # videos analyzed through the website (kept out of git)
DEFAULT_AUDIENCE = "indie_founders"
VIDEO_TYPES = {".mp4", ".mov", ".m4v", ".webm"}
MAX_UPLOAD_MB = 200
MAX_ANALYSIS_COST = 0.50  # a cautious upper limit for analyzing one video, used for the budget check

app = FastAPI(title="Viralyst API")
# The website runs at a different address. Browsers block calls between addresses unless
# the server says it's allowed: that permission is called CORS.
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(), allow_methods=["*"], allow_headers=["*"])

SPEND = DailySpend()  # today's AI spending, checked against VIRALYST_DAILY_BUDGET


def refresh_key() -> bool:
    """Re-read backend/.env, so a key added while the server is running is picked up without a restart."""
    load_dotenv(BACKEND / ".env")
    return has_api_key()


def require_ai(code: str | None, max_cost: float) -> None:
    """Every request that spends money passes these checks first: a key, the access code, the budget."""
    if not refresh_key():
        raise HTTPException(400, MISSING_KEY)
    if not code_is_valid(code):
        if code:
            time.sleep(1)  # makes guessing codes one after another painfully slow
        raise HTTPException(403, "AI features on this site need the access code.")
    if not SPEND.can_spend(max_cost, daily_budget()):
        raise HTTPException(429, "Today's AI budget is used up. It resets at midnight UTC.")


# ---------- Which files the website may open ----------

def video_files() -> dict[str, Path]:
    """Every video brief, by id. Only files in this list can ever be opened, so a request
    can't trick the server into reading anything else on your computer."""
    files = {f"examples/{p.stem}": p for p in sorted(EXAMPLES.glob("*.json")) if not p.name.endswith(".audience.json")}
    files |= {f"uploads/{p.stem}": p for p in sorted(UPLOADS.glob("*.json"))}
    return files


def audience_files() -> dict[str, Path]:
    return {p.name.removesuffix(".audience.json"): p for p in sorted(EXAMPLES.glob("*.audience.json"))}


def lookup(files: dict[str, Path], key: str, kind: str) -> Path:
    if key not in files:
        raise HTTPException(404, f"No {kind} called {key!r}.")
    return files[key]


def load_video(video_id: str, audience_id: str | None = None) -> tuple[VideoBrief, Audience]:
    brief, audience = load_example(lookup(video_files(), video_id, "video"))
    if audience_id:
        audience = load_audience(lookup(audience_files(), audience_id, "audience"))
    return brief, audience


# ---------- Turning results into JSON for the website ----------

def reaction_json(r: Reaction) -> dict:
    p = r.persona
    return {
        "name": p.name, "age": p.age, "occupation": p.occupation, "location": p.location,
        "interests": p.interests, "moment": p.moment, "in_target": p.in_target,
        "scrolled_past": r.scrolled_past, "watch": round(r.watch_fraction, 3),
        "liked": r.liked, "commented": r.commented, "shared": r.shared, "saved": r.saved, "followed": r.followed,
        "thought": r.thought, "comment": r.comment,
    }


def wave_json(result: WaveResult) -> dict:
    return {
        "type": "wave", "number": result.number, "label": result.wave.label, "represents": result.wave.represents,
        "rates": result.rates, "score": result.score, "threshold": result.threshold, "passed": result.passed,
        "reactions": [reaction_json(r) for r in result.reactions],
    }


def done_json(results: list[WaveResult], agent) -> dict:
    reactions = all_reactions(results)
    stage = furthest_stage(results)
    strengths = signals(reactions, results[0].benchmarks)
    worst = weakest(strengths)
    usage = getattr(agent, "usage", None)  # only the AI agent has one
    return {
        "type": "done", "stage": stage, "verdict": STAGES[stage], "reach": reach(results),
        "scroll_rate": scroll_rate(reactions), "segments": segments(reactions),
        "signals": strengths, "weakest": worst, "tip": TIPS[worst],
        "usage": {"calls": usage.calls, "reused": usage.reused, "failures": usage.failures,
                  "cost": round(usage.cost, 4)} if usage else None,
    }


def sse(event: dict) -> str:
    """One Server-Sent Event: "data: <json>" followed by a blank line.
    The browser receives each one the moment it's sent, without waiting for the rest."""
    return f"data: {json.dumps(event)}\n\n"


# ---------- Endpoints ----------

@app.get("/api/status")
def status(code: str | None = Header(None, alias=CODE_HEADER)) -> dict:
    unlocked = code_is_valid(code)
    return {
        "ai_available": refresh_key(),
        "ai_locked": access_code_required(),  # does this server want an access code?
        "ai_unlocked": unlocked,  # ...and did this request bring the right one?
        "budget": {"limit": daily_budget(), "spent_today": round(SPEND.spent_today(), 4)} if unlocked else None,
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "models": list(PRICES),
        "default_model": DEFAULT_MODEL,
    }


@app.get("/api/examples")
def examples() -> dict:
    videos = []
    for video_id, path in video_files().items():
        data = json.loads(path.read_text())
        audience = data["audience"] if isinstance(data["audience"], str) else None
        videos.append({
            "id": video_id,
            "title": data["video"]["title"],
            "hook": data["video"]["hook"],
            "length_seconds": data["video"]["length_seconds"],
            "uploaded": video_id.startswith("uploads/"),
            "audience": Path(audience).name.removesuffix(".audience.json") if audience else None,
            "analysis": data.get("analysis"),
        })
    audiences = []
    for audience_id, path in audience_files().items():
        audience = load_audience(path)
        audiences.append({"id": audience_id, "description": audience.description, "interests": audience.interests,
                          "kinds_of_people": len(audience.archetypes)})
    return {"videos": videos, "audiences": audiences}


@app.get("/api/estimate")
def estimate(video: str, model: str = DEFAULT_MODEL) -> dict:
    """What a full AI run could cost at most, so the website can ask before spending."""
    if model not in PRICES:
        raise HTTPException(400, f"Unknown model {model!r}.")
    brief, _ = load_video(video)
    calls = sum(wave.size for wave in WAVES)
    return {"max_calls": calls, "max_cost": round(estimate_cost(model, brief, calls), 2)}


@app.get("/api/simulate")
def simulate_live(video: str, audience: str | None = None, agent: Literal["rules", "ai"] = "rules",
                  model: str = DEFAULT_MODEL, seed: int | None = None,
                  code: str | None = Header(None, alias=CODE_HEADER)) -> StreamingResponse:
    """Run one simulation and stream it: a "start" event, one "wave" event per wave, then "done"."""
    brief, crowd_audience = load_video(video, audience)
    if model not in PRICES:
        raise HTTPException(400, f"Unknown model {model!r}.")
    if agent == "ai":
        require_ai(code, max_cost=estimate_cost(model, brief, sum(wave.size for wave in WAVES)))
    brain = LLMAgent(model) if agent == "ai" else MockAgent()
    seed = seed if seed is not None else random.randrange(10_000)

    def events():
        yield sse({"type": "start", "seed": seed, "agent": agent, "video": asdict(brief),
                   "waves": [asdict(wave) for wave in WAVES]})
        results = []
        try:
            for result in simulate(brief, crowd_audience, brain, seed):
                results.append(result)
                yield sse(wave_json(result))
            yield sse(done_json(results, brain))
        except anthropic.AuthenticationError:
            yield sse({"type": "error", "message": BAD_KEY})
        except Exception as error:  # tell the page what went wrong instead of silently stopping
            yield sse({"type": "error", "message": str(error)})
        finally:
            if agent == "ai":
                SPEND.record(brain.usage.cost)  # count what was really spent, even if the run failed

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/odds")
def odds(video: str, audience: str | None = None, runs: int = Query(200, ge=10, le=1000), seed: int = 0) -> dict:
    """Many free (rules-based) simulations, to show how often each outcome happens."""
    brief, crowd_audience = load_video(video, audience)
    agent = MockAgent()
    all_results = [run_cascade(brief, crowd_audience, agent, seed + i) for i in range(runs)]
    model = load_model()
    calibration = None
    if model and model.agent == "rules":  # these odds come from the rules personas
        mean_stage = sum(furthest_stage(results) for results in all_results) / runs
        calibration = {"views_per_follower": model.views_per_follower(mean_stage), "videos": model.videos,
                       "typical_miss": model.typical_miss}
    return {"runs": runs, "calibration": calibration,
            "outcomes": [{"stage": stage, "label": STAGES[stage], "share": share}
                         for stage, share in outcome_odds(all_results).items()]}


@app.get("/api/compare")
def compare_videos(videos: list[str] = Query(...), audience: str | None = None,
                   runs: int = Query(200, ge=10, le=1000), seed: int = 0) -> dict:
    """A/B test with free (rules-based) personas. The first video is the baseline."""
    if not 2 <= len(videos) <= 6:
        raise HTTPException(400, "Compare between two and six videos.")
    first, shared_audience = load_video(videos[0], audience)
    briefs = [first] + [load_video(video_id)[0] for video_id in videos[1:]]  # all on the same audience

    agent = MockAgent()
    arms = [run_arm(chr(ord("A") + i), brief, shared_audience, agent, runs, seed) for i, brief in enumerate(briefs)]
    return {
        "runs": runs,
        "arms": [{
            "name": arm.name, "video": video_id, "title": arm.title, "mean_stage": arm.mean_stage,
            "breakout_rate": arm.breakout_rate, "breakout_low": arm.breakout_range[0], "breakout_high": arm.breakout_range[1],
            "odds": [{"stage": stage, "label": STAGES[stage], "share": share} for stage, share in arm.odds.items()],
        } for arm, video_id in zip(arms, videos)],
        "comparisons": [{
            "challenger": c.challenger.name, "difference": c.difference, "low": c.low, "high": c.high, "verdict": c.verdict,
        } for c in (compare(arms[0], challenger) for challenger in arms[1:])],
    }


def claude_client():
    """A FastAPI "dependency": the endpoint asks for it, and tests can swap in a fake Claude."""
    refresh_key()
    return anthropic.Anthropic(max_retries=6)


def speech_to_text():
    return transcribe


@app.post("/api/analyze")
def analyze_upload(file: UploadFile = File(...), caption: str = Form(""), audience: str = Form(DEFAULT_AUDIENCE),
                   model: str = Form(DEFAULT_MODEL), client=Depends(claude_client),
                   listen=Depends(speech_to_text), code: str | None = Header(None, alias=CODE_HEADER)) -> dict:
    """Upload a video; get back its brief and Claude's feedback. It's then available to simulate."""
    require_ai(code, MAX_ANALYSIS_COST)
    try:
        require_ffmpeg()
    except MissingFFmpeg as error:
        raise HTTPException(500, str(error))
    if model not in PRICES:
        raise HTTPException(400, f"Unknown model {model!r}.")
    audience_path = lookup(audience_files(), audience, "audience")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in VIDEO_TYPES:
        raise HTTPException(400, "Please upload an .mp4, .mov, .m4v or .webm video.")

    # Save the upload under a random name, never the name the browser sent.
    video_id = uuid.uuid4().hex[:12]
    UPLOADS.mkdir(exist_ok=True)
    video_path = UPLOADS / f"{video_id}{suffix}"
    with video_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    if video_path.stat().st_size > MAX_UPLOAD_MB * 1024 * 1024:
        video_path.unlink()
        raise HTTPException(413, f"That video is over {MAX_UPLOAD_MB} MB.")

    out_path = UPLOADS / f"{video_id}.json"
    try:
        with tempfile.TemporaryDirectory() as work:
            prepared = prepare(video_path, Path(work), transcriber=listen)
            analysis, usage = analyze(prepared.video, prepared.frames, prepared.transcript, caption, client, model)
    except anthropic.AuthenticationError:
        raise HTTPException(401, BAD_KEY)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(422, f"Couldn't analyze that video: {error}")

    SPEND.record(usage.cost)
    result = build_result(prepared, analysis, caption, audience_path, out_path, model)
    save_result(result, out_path)
    return {"id": f"uploads/{video_id}", **result, "cost": round(usage.cost, 4)}
