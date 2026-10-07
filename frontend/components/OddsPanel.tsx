"use client";

import { useState } from "react";
import { getOdds } from "@/lib/api";
import type { Odds } from "@/lib/types";

const COLORS = ["var(--bad)", "var(--warn)", "var(--accent)", "var(--good)", "var(--good)"];

export default function OddsPanel({ video, audience }: { video: string; audience: string }) {
  const [odds, setOdds] = useState<Odds | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [forVideo, setForVideo] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      setOdds(await getOdds(video, audience));
      setForVideo(`${video}|${audience}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  const stale = odds && forVideo !== `${video}|${audience}`;
  return (
    <div className="rounded-xl border border-border bg-panel p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-medium">The odds</h3>
          <p className="text-sm text-muted">One run is one possible future. Run it many times to see how often each outcome happens.</p>
        </div>
        <button onClick={run} disabled={loading}
                className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-bg disabled:opacity-50">
          {loading ? "Simulating…" : "Run 200 free simulations"}
        </button>
      </div>
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      {odds && !stale && (
        <div className="mt-4 space-y-2">
          {odds.outcomes.map((o, i) => (
            <div key={o.stage} className="grid grid-cols-[3rem_1fr] items-center gap-3 text-sm">
              <span className="text-right tabular-nums">{Math.round(o.share * 100)}%</span>
              <div>
                <div className="h-2 rounded-full bg-border">
                  <div className="h-2 rounded-full" style={{ width: `${o.share * 100}%`, background: COLORS[i] }} />
                </div>
                <p className="mt-0.5 text-xs text-muted">{o.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}
      {odds && !stale && odds.calibration && (
        <p className="mt-3 text-sm">
          Calibrated on {odds.calibration.videos} of your real videos: expect about{" "}
          <span className="font-medium">{odds.calibration.views_per_follower.toFixed(1)}× your follower count</span> in views
          (usually within {odds.calibration.typical_miss.toFixed(1)}×).
        </p>
      )}
      {stale && <p className="mt-3 text-sm text-muted">You changed the video or audience. Run again to update.</p>}
    </div>
  );
}
