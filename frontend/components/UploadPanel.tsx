"use client";

import { useState } from "react";
import { analyzeVideo } from "@/lib/api";
import type { AnalyzeResult, Status } from "@/lib/types";

type Props = { status: Status; audience: string; onAnalyzed: (result: AnalyzeResult) => void };

export default function UploadPanel({ status, audience, onAnalyzed }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);

  const blocked = !status.ai_available
    ? "Add your Claude API key to backend/.env to analyze your own videos. It's picked up automatically, no restart needed."
    : !status.ai_unlocked
      ? "Analyzing videos uses AI, which is locked on this site. Unlock it with the access code in the settings."
      : !status.ffmpeg_available
      ? "Install ffmpeg (brew install ffmpeg) to analyze videos."
      : "";

  async function upload() {
    if (!file) return;
    if (!window.confirm("Claude will watch this video. That costs about $0.10–0.20. Continue?")) return;
    setBusy(true);
    setError("");
    try {
      const analyzed = await analyzeVideo(file, caption, audience);
      setResult(analyzed);
      onAnalyzed(analyzed);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-panel p-5">
      <h3 className="font-medium">Analyze your own video</h3>
      <p className="text-sm text-muted">
        Viralyst takes frames, listens with Whisper on your machine, and Claude writes the brief.
      </p>
      {blocked ? (
        <p className="mt-3 rounded-lg bg-bg px-3 py-2 text-sm">{blocked}</p>
      ) : (
        <div className="mt-3 space-y-2">
          <input type="file" accept="video/mp4,video/quicktime,video/webm,.m4v"
                 onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="block w-full text-sm" />
          <input value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Caption you plan to post (optional)"
                 className="w-full rounded-lg border border-border bg-bg px-3 py-1.5 text-sm" />
          <button onClick={upload} disabled={!file || busy}
                  className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50">
            {busy ? "Watching the video… (about a minute)" : "Analyze video"}
          </button>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      {result && (
        <div className="mt-4 space-y-2 text-sm">
          <p>
            <span className="text-muted">Hook:</span> {result.video.hook}
          </p>
          <p className="tabular-nums">
            Hook {result.video.hook_strength.toFixed(2)} · quality {result.video.quality.toFixed(2)} · shareability{" "}
            {result.video.shareability.toFixed(2)} · save value {result.video.save_value.toFixed(2)}
          </p>
          <ul className="space-y-0.5">
            {result.analysis.strengths.map((s) => <li key={s} className="text-good">+ {s}</li>)}
            {result.analysis.weaknesses.map((w) => <li key={w} className="text-bad">− {w}</li>)}
          </ul>
          <p>
            <span className="text-muted">Try opening with:</span> “{result.analysis.better_hook}”
          </p>
          <p className="text-muted">Selected above. Press “Run simulation” to see how it spreads. Cost: ${result.cost.toFixed(2)}</p>
        </div>
      )}
    </div>
  );
}
