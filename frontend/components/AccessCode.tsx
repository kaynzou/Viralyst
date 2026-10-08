"use client";

import { useState } from "react";
import { setAccessCode } from "@/lib/api";
import type { Status } from "@/lib/types";

type Props = {
  status: Status;
  /** Re-checks the status with the stored code and returns the new status. */
  recheck: () => Promise<Status | null>;
};

/** Online, the server can lock AI features behind a code. Locally there's no lock, so this shows nothing. */
export default function AccessCode({ status, recheck }: Props) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  if (!status.ai_available || !status.ai_locked) return null;

  async function unlock() {
    setAccessCode(code.trim());
    const fresh = await recheck();
    if (fresh?.ai_unlocked) {
      setCode("");
      setError("");
    } else {
      setAccessCode(""); // don't keep a wrong code
      setError("That code didn't work.");
    }
  }

  async function lock() {
    setAccessCode("");
    await recheck();
  }

  if (status.ai_unlocked) {
    const budget = status.budget;
    return (
      <p className="mt-2 rounded-lg bg-bg px-3 py-2 text-xs">
        AI unlocked in this browser
        {budget?.limit != null && <> · spent today ${budget.spent_today.toFixed(2)} of ${budget.limit.toFixed(2)}</>}.{" "}
        <button onClick={lock} className="underline">Lock</button>
      </p>
    );
  }

  return (
    <div className="mt-2 space-y-1.5">
      <p className="text-xs text-muted">AI features are locked on this site. Enter the access code to use them.</p>
      <div className="flex gap-2">
        <input type="password" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Access code"
               onKeyDown={(e) => e.key === "Enter" && code.trim() && unlock()}
               className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-2 py-1.5" />
        <button onClick={unlock} disabled={!code.trim()}
                className="rounded-lg border border-border px-3 py-1.5 hover:bg-bg disabled:opacity-50">
          Unlock
        </button>
      </div>
      {error && <p className="text-xs text-bad">{error}</p>}
    </div>
  );
}
