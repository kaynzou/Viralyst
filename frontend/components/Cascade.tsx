import type { Reaction, WaveEvent, WaveInfo } from "@/lib/types";

// The strongest thing each person did decides their dot's color.
export const ACTIONS = [
  { key: "shared", label: "Shared", color: "var(--good)" },
  { key: "saved", label: "Saved", color: "var(--warn)" },
  { key: "commented", label: "Commented", color: "var(--comment)" },
  { key: "liked", label: "Liked", color: "var(--like)" },
] as const;

export function dotColor(r: Reaction): string {
  if (r.scrolled_past) return "var(--idle)";
  const action = ACTIONS.find((a) => r[a.key]);
  if (action) return action.color;
  // Only watched: the longer they watched, the stronger the blue.
  return `color-mix(in srgb, var(--accent) ${Math.round(35 + 65 * r.watch)}%, transparent)`;
}

function Legend() {
  const items = [
    { label: "Scrolled past", color: "var(--idle)" },
    { label: "Watched (darker = longer)", color: "var(--accent)" },
    ...ACTIONS.slice().reverse(),
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
      {items.map((item) => (
        <span key={item.label} className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: item.color }} />
          {item.label}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-full border border-muted" /> target audience
        <span className="ml-2 inline-block h-2.5 w-2.5 rounded-[2px] border border-muted" /> everyone else
      </span>
    </div>
  );
}

function ScoreMeter({ wave }: { wave: WaveEvent }) {
  const max = 3;
  const width = `${(Math.min(wave.score, max) / max) * 100}%`;
  const threshold = `${(wave.threshold / max) * 100}%`;
  const color = wave.passed ? "var(--good)" : "var(--bad)";
  return (
    <div className="mt-3">
      <div className="relative h-2 rounded-full bg-border">
        <div className="h-2 rounded-full transition-all duration-700" style={{ width, background: color }} />
        <div className="absolute -top-1 h-4 w-0.5 bg-text" style={{ left: threshold }} title="A typical reel scores 1.0" />
      </div>
      <p className="mt-1.5 text-sm">
        Score <b>{wave.score.toFixed(2)}</b> vs a typical reel (1.00):{" "}
        <span style={{ color }} className="font-medium">
          {wave.passed ? "pushed to the next wave" : "the algorithm stopped here"}
        </span>
      </p>
    </div>
  );
}

type WaveCardProps = {
  number: number;
  info: WaveInfo;
  wave?: WaveEvent;
  state: "waiting" | "shown" | "not reached";
  selected: Reaction | null;
  onSelect: (r: Reaction) => void;
};

function WaveCard({ number, info, wave, state, selected, onSelect }: WaveCardProps) {
  const target = wave ? wave.reactions.filter((r) => r.in_target).length / wave.reactions.length : info.target_fraction;
  return (
    <section className={`rounded-xl border border-border bg-panel p-4 ${state === "not reached" ? "opacity-45" : ""}`}>
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium">
          Wave {number} <span className="text-muted">· {info.label}</span>
        </h3>
        <span className="text-xs text-muted">
          {info.size} people · {Math.round(target * 100)}% target audience · stands for ~{info.represents.toLocaleString()}
        </span>
      </header>

      {state === "waiting" && <p className="mt-3 text-sm text-muted">Waiting for this wave…</p>}
      {state === "not reached" && <p className="mt-3 text-sm text-muted">Never shown: the algorithm stopped earlier.</p>}
      {state === "shown" && wave && (
        <>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {wave.reactions.map((r, i) => (
              <button
                key={i}
                onClick={() => onSelect(r)}
                title={`${r.name}, ${r.age}`}
                className={`dot h-3 w-3 ${r.in_target ? "rounded-full" : "rounded-[2px]"} ${
                  selected === r ? "ring-2 ring-text ring-offset-1 ring-offset-panel" : ""
                }`}
                style={{ background: dotColor(r), animationDelay: `${i * 6}ms` }}
              />
            ))}
          </div>
          <ScoreMeter wave={wave} />
        </>
      )}
    </section>
  );
}

type CascadeProps = {
  waves: WaveInfo[];
  results: WaveEvent[];
  revealed: number;
  finished: boolean;
  selected: Reaction | null;
  onSelect: (r: Reaction) => void;
};

export default function Cascade({ waves, results, revealed, finished, selected, onSelect }: CascadeProps) {
  return (
    <div className="space-y-3">
      <Legend />
      {waves.map((info, i) => {
        const shown = i < revealed && results[i];
        const state = shown ? "shown" : finished && i >= results.length ? "not reached" : "waiting";
        return (
          <WaveCard key={i} number={i + 1} info={info} wave={results[i]} state={state}
                    selected={selected} onSelect={onSelect} />
        );
      })}
    </div>
  );
}
