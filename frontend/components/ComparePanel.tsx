"use client";

import { useState } from "react";
import { getComparison } from "@/lib/api";
import type { CompareArm, CompareResult, VideoOption } from "@/lib/types";

const percent = (x: number) => `${Math.round(x * 100)}%`;

function ArmRow({ arm }: { arm: CompareArm }) {
  return (
    <div className="space-y-1">
      <p className="text-sm">
        <span className="font-medium">{arm.name}</span> <span className="text-muted">· {arm.title}</span>
      </p>
      {/* The solid bar is the breakout rate; the lighter band around its end is the 95% range. */}
      <div className="relative h-3 rounded-full bg-border">
        <div className="absolute h-3 rounded-full bg-accent" style={{ width: `${arm.breakout_rate * 100}%` }} />
        <div className="absolute top-0 h-3 rounded-full bg-accent opacity-30"
             style={{ left: `${arm.breakout_low * 100}%`, width: `${(arm.breakout_high - arm.breakout_low) * 100}%` }} />
      </div>
      <p className="text-xs text-muted tabular-nums">
        Breaks out in {percent(arm.breakout_rate)} of runs (95% range {percent(arm.breakout_low)}–{percent(arm.breakout_high)}) ·
        average stage {arm.mean_stage.toFixed(1)} of 5
      </p>
    </div>
  );
}

export default function ComparePanel({ videos, audience, current }: { videos: VideoOption[]; audience: string; current: string }) {
  const other = videos.find((v) => v.id !== current)?.id ?? current;
  const [a, setA] = useState(current);
  const [b, setB] = useState(other);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      setResult(await getComparison([a, b], audience));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  const select = (value: string, onChange: (id: string) => void, label: string) => (
    <label className="block flex-1 text-sm">
      <span className="text-muted">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg px-2 py-1.5">
        {videos.map((v) => <option key={v.id} value={v.id}>{v.title}</option>)}
      </select>
    </label>
  );

  const comparison = result?.comparisons[0];
  const decided = comparison && !comparison.verdict.startsWith("Too close");
  return (
    <div className="rounded-xl border border-border bg-panel p-5">
      <h3 className="font-medium">A/B test</h3>
      <p className="text-sm text-muted">
        Which version spreads further? Both are shown to the same audience with the same seeds, 200 free simulations each.
      </p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        {select(a, setA, "A (baseline)")}
        {select(b, setB, "B (challenger)")}
      </div>
      <button onClick={run} disabled={loading || a === b}
              className="mt-3 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-bg disabled:opacity-50">
        {loading ? "Simulating…" : a === b ? "Pick two different videos" : "Compare"}
      </button>
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      {result && comparison && (
        <div className="mt-4 space-y-3">
          {result.arms.map((arm) => <ArmRow key={arm.name} arm={arm} />)}
          <p className="text-sm">
            <span className="tabular-nums">
              B vs A: {comparison.difference >= 0 ? "+" : ""}{Math.round(comparison.difference * 100)} points (95% range{" "}
              {Math.round(comparison.low * 100)} to {Math.round(comparison.high * 100)}).{" "}
            </span>
            <span className={decided ? "font-medium text-good" : "text-muted"}>{comparison.verdict}.</span>
          </p>
        </div>
      )}
    </div>
  );
}
