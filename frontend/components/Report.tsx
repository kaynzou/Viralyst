import type { DoneEvent, Reaction, Signal } from "@/lib/types";

const SIGNAL_LABELS: Record<Signal, string> = {
  watch: "Watch time",
  share: "Shares",
  save: "Saves",
  comment: "Comments",
  like: "Likes",
  follow: "Follows",
};

function stageColor(stage: number): string {
  if (stage >= 4) return "var(--good)";
  if (stage === 3) return "var(--accent)";
  return "var(--bad)";
}

const percent = (x: number) => `${Math.round(x * 100)}%`;

export default function Report({ done, reactions }: { done: DoneEvent; reactions: Reaction[] }) {
  const [word, meaning] = done.verdict.split(": ");
  const comments = reactions.filter((r) => r.comment);
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-panel p-5">
        <p className="text-sm text-muted">Verdict</p>
        <p className="mt-1 text-3xl font-semibold tracking-tight" style={{ color: stageColor(done.stage) }}>
          {word}
        </p>
        <p className="mt-1 text-muted">{meaning}</p>
        <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div>
            <dt className="text-muted">Rough reach</dt>
            <dd className="font-medium">~{done.reach.toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-muted">Scrolled past</dt>
            <dd className="font-medium">{percent(done.scroll_rate)}</dd>
          </div>
          <div>
            <dt className="text-muted">Viewers simulated</dt>
            <dd className="font-medium">{reactions.length}</dd>
          </div>
        </dl>
        <p className="mt-2 text-xs text-muted">Reach is an uncalibrated guess until it&apos;s checked against real results.</p>
      </div>

      <div className="rounded-xl border border-border bg-panel p-5">
        <h3 className="font-medium">Signals vs a typical reel</h3>
        <div className="mt-3 space-y-2">
          {(Object.keys(SIGNAL_LABELS) as Signal[]).map((signal) => {
            const value = done.signals[signal];
            const weakest = signal === done.weakest;
            return (
              <div key={signal} className="grid grid-cols-[6.5rem_1fr_3rem] items-center gap-3 text-sm">
                <span className={weakest ? "font-medium text-bad" : ""}>{SIGNAL_LABELS[signal]}</span>
                <div className="relative h-2 rounded-full bg-border">
                  <div className="h-2 rounded-full" style={{ width: `${(Math.min(value, 3) / 3) * 100}%`,
                    background: weakest ? "var(--bad)" : "var(--accent)" }} />
                  <div className="absolute -top-1 h-4 w-0.5 bg-text" style={{ left: "33.3%" }} />
                </div>
                <span className="text-right tabular-nums">{value.toFixed(1)}×</span>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-sm">
          <span className="font-medium">Weakest: {SIGNAL_LABELS[done.weakest].toLowerCase()}.</span> {done.tip}
        </p>
        {done.scroll_rate > 0.5 && (
          <p className="mt-2 text-sm font-medium text-bad">
            Most viewers scrolled past instantly: fix the first 3 seconds before anything else.
          </p>
        )}
      </div>

      <div className="rounded-xl border border-border bg-panel p-5">
        <h3 className="font-medium">Who engaged</h3>
        <table className="mt-3 w-full text-sm">
          <thead className="text-left text-muted">
            <tr><th className="font-normal" /><th className="font-normal">Viewers</th><th className="font-normal">Watched</th>
              <th className="font-normal">Liked</th><th className="font-normal">Shared</th></tr>
          </thead>
          <tbody>
            {([["Target audience", done.segments.target], ["Everyone else", done.segments.others]] as const).map(
              ([label, s]) => s && (
                <tr key={label} className="tabular-nums">
                  <td className="py-1">{label}</td><td>{s.viewers}</td><td>{percent(s.watch)}</td>
                  <td>{percent(s.like)}</td><td>{(s.share * 100).toFixed(1)}%</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>

      {comments.length > 0 && (
        <div className="rounded-xl border border-border bg-panel p-5">
          <h3 className="font-medium">What people commented ({comments.length})</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {comments.slice(0, 10).map((r, i) => (
              <li key={i} className="rounded-lg bg-bg px-3 py-2">
                {r.comment} <span className="text-muted">· {r.name}, {r.in_target ? "target audience" : "outside target"}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {done.usage && (
        <p className="text-sm text-muted">
          AI cost for this run: ${done.usage.cost.toFixed(2)} ({done.usage.calls} calls to Claude, {done.usage.reused} answers
          reused for free{done.usage.failures ? `, ${done.usage.failures} failed` : ""}).
        </p>
      )}
    </div>
  );
}
