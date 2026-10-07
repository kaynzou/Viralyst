"use client";
// "use client" = this component runs in the browser, so it can use state, clicks and live connections.

import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL, getEstimate, getExamples, getStatus, streamSimulation } from "@/lib/api";
import type { AnalyzeResult, DoneEvent, Examples, Reaction, StartEvent, Status, WaveEvent } from "@/lib/types";
import Cascade from "./Cascade";
import OddsPanel from "./OddsPanel";
import PersonaCard from "./PersonaCard";
import Report from "./Report";
import UploadPanel from "./UploadPanel";

type Run = {
  status: "idle" | "running" | "done" | "error";
  start?: StartEvent;
  waves: WaveEvent[];
  done?: DoneEvent;
  error?: string;
};

const IDLE: Run = { status: "idle", waves: [] };

export default function Simulator() {
  const [status, setStatus] = useState<Status | null>(null);
  const [examples, setExamples] = useState<Examples | null>(null);
  const [apiDown, setApiDown] = useState(false);

  const [videoId, setVideoId] = useState("");
  const [audienceId, setAudienceId] = useState("");
  const [agent, setAgent] = useState<"rules" | "ai">("rules");
  const [model, setModel] = useState("");
  const [seed, setSeed] = useState("");

  const [run, setRun] = useState<Run>(IDLE);
  const [revealed, setRevealed] = useState(0); // how many waves are drawn so far
  const [selected, setSelected] = useState<Reaction | null>(null);
  const stop = useRef<(() => void) | null>(null);
  const linkChecked = useRef(false);

  /** Stream one simulation into the page. Takes every setting as an argument, so it never reads stale state. */
  const startStream = useCallback((params: Record<string, string>) => {
    stop.current?.();
    setSelected(null);
    setRevealed(0);
    setRun({ status: "running", waves: [] });
    stop.current = streamSimulation(params, (event) => {
      if (event.type === "start") {
        // Put this run in the address bar, so copying the link reproduces it exactly.
        const link = new URLSearchParams({ video: params.video, audience: params.audience, seed: String(event.seed), run: "1" });
        window.history.replaceState(null, "", `?${link}`);
      }
      setRun((current) => {
        switch (event.type) {
          case "start": return { ...current, start: event };
          case "wave": return { ...current, waves: [...current.waves, event] };
          case "done": return { ...current, status: "done", done: event };
          case "error": return { ...current, status: "error", error: event.message };
        }
      });
    });
  }, []);

  const load = useCallback(async (selectId?: string) => {
    try {
      const [newStatus, newExamples] = await Promise.all([getStatus(), getExamples()]);
      setStatus(newStatus);
      setExamples(newExamples);
      setApiDown(false);
      setModel((m) => m || newStatus.default_model);

      // The first time, open the run described in the address bar (a shared link), if there is one.
      if (!linkChecked.current) {
        linkChecked.current = true;
        const query = new URLSearchParams(window.location.search);
        const linked = newExamples.videos.find((v) => v.id === query.get("video"));
        if (linked) {
          const known = newExamples.audiences.some((a) => a.id === query.get("audience"));
          const audience = known ? query.get("audience")! : linked.audience ?? newExamples.audiences[0]?.id ?? "";
          const linkedSeed = (query.get("seed") ?? "").replace(/\D/g, "");
          setVideoId(linked.id);
          setAudienceId(audience);
          setSeed(linkedSeed);
          if (query.get("run") === "1") {
            // A link only ever starts the free rules mode: opening a link must never spend money.
            startStream({ video: linked.id, audience, agent: "rules", model: newStatus.default_model,
                          ...(linkedSeed ? { seed: linkedSeed } : {}) });
          }
          return;
        }
      }

      const first = newExamples.videos.find((v) => v.id === selectId) ?? newExamples.videos[0];
      setVideoId((current) => (selectId || !current ? first?.id ?? "" : current));
      setAudienceId((current) => (selectId || !current ? first?.audience ?? newExamples.audiences[0]?.id ?? "" : current));
    } catch {
      setApiDown(true);
    }
  }, [startStream]);

  // Load once when the page opens, and re-check whenever you come back to this tab
  // (so a newly added API key or a freshly started server shows up).
  useEffect(() => {
    const refresh = () => void load();
    refresh();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [load]);

  // Stop any running simulation when the page closes.
  useEffect(() => () => stop.current?.(), []);

  // Draw waves one at a time, so you can watch the cascade even when results arrive instantly.
  useEffect(() => {
    if (revealed >= run.waves.length) return;
    const previous = run.waves[revealed - 1];
    const delay = previous ? Math.min(2500, previous.reactions.length * 6 + 900) : 150;
    const timer = setTimeout(() => setRevealed((r) => r + 1), delay);
    return () => clearTimeout(timer);
  }, [revealed, run.waves]);

  function chooseVideo(id: string) {
    setVideoId(id);
    const video = examples?.videos.find((v) => v.id === id);
    if (video?.audience) setAudienceId(video.audience);
  }

  async function startRun() {
    if (!videoId) return;
    if (agent === "ai") {
      const estimate = await getEstimate(videoId, model);
      const ok = window.confirm(
        `AI personas: up to ${estimate.max_calls} calls to ${model}, costing up to $${estimate.max_cost.toFixed(2)}.\n` +
          "Videos that stop early cost less, and answers already saved are free. Continue?",
      );
      if (!ok) return;
    }
    const params: Record<string, string> = { video: videoId, audience: audienceId, agent, model };
    if (seed.trim()) params.seed = seed.trim();
    startStream(params);
  }

  function onAnalyzed(result: AnalyzeResult) {
    void load(result.id); // refresh the list and select the new video
  }

  const video = examples?.videos.find((v) => v.id === videoId);
  const allReactions = run.waves.flatMap((w) => w.reactions);
  const finished = run.status === "done" || run.status === "error";
  const showReport = run.done && revealed >= run.waves.length;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Viralyst</h1>
          <p className="text-muted">Test your product demo on a simulated Instagram audience before you post it.</p>
        </div>
        {status && (
          <div className="flex gap-2 text-xs">
            <span className="rounded-full border border-border px-2.5 py-1">
              <span className="text-good">●</span> API connected
            </span>
            <span className="rounded-full border border-border px-2.5 py-1">
              {status.ai_available ? <><span className="text-good">●</span> AI features on</>
                : <><span className="text-muted">○</span> AI features off (no API key)</>}
            </span>
          </div>
        )}
      </header>

      {apiDown && (
        <div className="mt-6 rounded-xl border border-bad p-5 text-sm">
          <p className="font-medium">Can&apos;t reach the Viralyst API at {API_URL}.</p>
          <p className="mt-1 text-muted">Start it in a terminal, then come back to this tab:</p>
          <pre className="mt-2 rounded-lg bg-panel p-3 font-mono text-xs">cd ~/viralyst/backend{"\n"}uv run fastapi dev viralyst/api.py</pre>
        </div>
      )}

      {examples && status && (
        <div className="mt-6 grid gap-6 lg:grid-cols-[22rem_1fr]">
          <aside className="space-y-4">
            <div className="space-y-3 rounded-xl border border-border bg-panel p-5 text-sm">
              <label className="block">
                <span className="text-muted">Video</span>
                <select value={videoId} onChange={(e) => chooseVideo(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-border bg-bg px-2 py-1.5">
                  {[false, true].map((uploaded) => {
                    const group = examples.videos.filter((v) => v.uploaded === uploaded);
                    return group.length > 0 && (
                      <optgroup key={String(uploaded)} label={uploaded ? "Your videos" : "Examples"}>
                        {group.map((v) => <option key={v.id} value={v.id}>{v.title}</option>)}
                      </optgroup>
                    );
                  })}
                </select>
              </label>
              {video && <p className="text-xs text-muted">First 3 seconds: {video.hook}</p>}

              <label className="block">
                <span className="text-muted">Audience</span>
                <select value={audienceId} onChange={(e) => setAudienceId(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-border bg-bg px-2 py-1.5">
                  {examples.audiences.map((a) => <option key={a.id} value={a.id}>{a.id.replaceAll("_", " ")}</option>)}
                </select>
              </label>

              <fieldset>
                <legend className="text-muted">Personas</legend>
                <label className="mt-1 flex items-center gap-2">
                  <input type="radio" checked={agent === "rules"} onChange={() => setAgent("rules")} />
                  Rules: free and instant
                </label>
                <label className={`flex items-center gap-2 ${status.ai_available ? "" : "opacity-50"}`}>
                  <input type="radio" checked={agent === "ai"} disabled={!status.ai_available} onChange={() => setAgent("ai")} />
                  AI: played by Claude (costs money)
                </label>
                {!status.ai_available && <p className="mt-1 text-xs text-muted">Needs a Claude API key in backend/.env.</p>}
                {agent === "ai" && (
                  <select value={model} onChange={(e) => setModel(e.target.value)}
                          className="mt-2 w-full rounded-lg border border-border bg-bg px-2 py-1.5">
                    {status.models.map((m) => <option key={m}>{m}</option>)}
                  </select>
                )}
              </fieldset>

              <label className="block">
                <span className="text-muted">Seed (optional)</span>
                <input value={seed} onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))} placeholder="random"
                       className="mt-1 w-full rounded-lg border border-border bg-bg px-2 py-1.5" />
                <span className="mt-1 block text-xs text-muted">Same seed = same people and same dice rolls.</span>
              </label>

              <button onClick={startRun} disabled={run.status === "running"}
                      className="w-full rounded-lg bg-accent px-3 py-2 font-medium text-on-accent disabled:opacity-50">
                {run.status === "running" ? "Simulating…" : "Run simulation"}
              </button>
            </div>

            <div className="lg:sticky lg:top-6">
              <PersonaCard person={selected} onClose={() => setSelected(null)} />
            </div>
          </aside>

          <section className="min-w-0 space-y-4">
            {run.status === "idle" ? (
              <div className="rounded-xl border border-dashed border-border p-8 text-center text-muted">
                Pick a video and press <span className="text-text">Run simulation</span> to watch it spread, wave by wave.
              </div>
            ) : (
              <>
                {run.start && (
                  <p className="text-sm text-muted">
                    “{run.start.video.title}” · seed {run.start.seed} ·{" "}
                    {run.start.agent === "ai" ? "AI personas" : "rule-based personas"}
                  </p>
                )}
                {run.error && <p className="rounded-xl border border-bad p-4 text-sm">{run.error}</p>}
                {run.start && (
                  <Cascade waves={run.start.waves} results={run.waves} revealed={revealed} finished={finished}
                           selected={selected} onSelect={setSelected} />
                )}
                {showReport && run.done && <Report done={run.done} reactions={allReactions} />}
              </>
            )}
            {videoId && <OddsPanel video={videoId} audience={audienceId} />}
            <UploadPanel status={status} audience={audienceId} onAnalyzed={onAnalyzed} />
          </section>
        </div>
      )}
    </main>
  );
}
