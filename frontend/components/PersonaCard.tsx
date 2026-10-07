import type { Reaction } from "@/lib/types";
import { dotColor } from "./Cascade";

function whatTheyDid(r: Reaction): string {
  if (r.scrolled_past) return "Scrolled past within a second or two.";
  const actions = (["liked", "commented", "shared", "saved", "followed"] as const).filter((a) => r[a]);
  const watched = `Watched ${Math.round(r.watch * 100)}% of the video`;
  return actions.length ? `${watched}, then ${actions.join(", ")}.` : `${watched}, then moved on.`;
}

export default function PersonaCard({ person, onClose }: { person: Reaction | null; onClose: () => void }) {
  if (!person) {
    return (
      <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted">
        Click any dot to meet that viewer.
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-border bg-panel p-4 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full" style={{ background: dotColor(person) }} />
          <h3 className="font-medium">
            {person.name}, {person.age}
          </h3>
        </div>
        <button onClick={onClose} className="text-muted hover:text-text" aria-label="Close">
          ✕
        </button>
      </div>
      {person.occupation && (
        <p className="mt-1 text-muted">
          {person.occupation}
          {person.location && ` · ${person.location}`}
        </p>
      )}
      <p className="mt-1 text-muted">
        Into {person.interests.join(", ")} · {person.in_target ? "in your target audience" : "outside your target audience"}
      </p>
      {person.moment && <p className="mt-1 text-muted">Scrolling {person.moment}</p>}
      <p className="mt-3">{whatTheyDid(person)}</p>
      {person.thought && <p className="mt-2 italic">“{person.thought}”</p>}
      {person.comment && (
        <p className="mt-2 rounded-lg bg-bg px-3 py-2">
          <span className="text-muted">Commented:</span> {person.comment}
        </p>
      )}
    </div>
  );
}
