// Everything the website asks the Python API. The API runs separately (port 8000 locally).
import type { AnalyzeResult, CompareResult, Examples, Odds, SimulationEvent, Status } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CODE_KEY = "viralyst-access-code";

/** The access code that unlocks AI features online. Remembered in this browser only. */
export function getAccessCode(): string {
  try {
    return localStorage.getItem(CODE_KEY) ?? "";
  } catch {
    return ""; // storage can be blocked (private windows): then it just isn't remembered
  }
}

export function setAccessCode(code: string): void {
  try {
    if (code) localStorage.setItem(CODE_KEY, code);
    else localStorage.removeItem(CODE_KEY);
  } catch {
    // see above
  }
}

// The code travels in a header, never in the address: addresses end up in history, logs and shared links.
function headers(): Record<string, string> {
  const code = getAccessCode();
  return code ? { "X-Viralyst-Code": code } : {};
}

async function errorMessage(response: Response): Promise<string> {
  const body = await response.json().catch(() => null);
  return body?.detail ?? `The API answered with error ${response.status}.`;
}

async function getJson<T>(path: string, params?: URLSearchParams | Record<string, string>): Promise<T> {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const response = await fetch(`${API_URL}${path}${query}`, { headers: headers() });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json();
}

export const getStatus = () => getJson<Status>("/api/status");
export const getExamples = () => getJson<Examples>("/api/examples");
export const getEstimate = (video: string, model: string) =>
  getJson<{ max_calls: number; max_cost: number }>("/api/estimate", { video, model });
export const getOdds = (video: string, audience: string, runs = 200) =>
  getJson<Odds>("/api/odds", { video, audience, runs: String(runs) });

export function getComparison(videos: string[], audience: string, runs = 200): Promise<CompareResult> {
  const params = new URLSearchParams({ audience, runs: String(runs) });
  for (const video of videos) params.append("videos", video); // the same name repeated = a list
  return getJson<CompareResult>("/api/compare", params);
}

export async function analyzeVideo(file: File, caption: string, audience: string): Promise<AnalyzeResult> {
  // FormData is how browsers send files: like a form with an attachment.
  const form = new FormData();
  form.append("file", file);
  form.append("caption", caption);
  form.append("audience", audience);
  const response = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: form, headers: headers() });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json();
}

/** Start a simulation and call `onEvent` for each event as it arrives. Returns a function that stops it. */
export function streamSimulation(params: Record<string, string>, onEvent: (event: SimulationEvent) => void): () => void {
  const controller = new AbortController();
  (async () => {
    try {
      const response = await fetch(`${API_URL}/api/simulate?${new URLSearchParams(params)}`, {
        headers: headers(),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        onEvent({ type: "error", message: await errorMessage(response) });
        return;
      }
      // Read the answer piece by piece as it arrives. Each event is "data: {...}" followed by a blank line.
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += value;
        let end;
        while ((end = buffer.indexOf("\n\n")) >= 0) {
          const chunk = buffer.slice(0, end);
          buffer = buffer.slice(end + 2);
          if (chunk.startsWith("data: ")) onEvent(JSON.parse(chunk.slice(6)));
        }
      }
    } catch {
      if (!controller.signal.aborted) onEvent({ type: "error", message: "Lost the connection to the Viralyst API." });
    }
  })();
  return () => controller.abort();
}
