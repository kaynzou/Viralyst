// Everything the website asks the Python API. The API runs separately, on port 8000.
import type { AnalyzeResult, CompareResult, Examples, Odds, SimulationEvent, Status } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const response = await fetch(`${API_URL}${path}${query}`);
  if (!response.ok) throw new Error((await response.json()).detail ?? `Request failed (${response.status})`);
  return response.json();
}

export const getStatus = () => getJson<Status>("/api/status");
export const getExamples = () => getJson<Examples>("/api/examples");
export const getEstimate = (video: string, model: string) =>
  getJson<{ max_calls: number; max_cost: number }>("/api/estimate", { video, model });
export const getOdds = (video: string, audience: string, runs = 200) =>
  getJson<Odds>("/api/odds", { video, audience, runs: String(runs) });

export async function getComparison(videos: string[], audience: string, runs = 200): Promise<CompareResult> {
  const params = new URLSearchParams({ audience, runs: String(runs) });
  for (const video of videos) params.append("videos", video); // the same name repeated = a list
  const response = await fetch(`${API_URL}/api/compare?${params}`);
  if (!response.ok) throw new Error((await response.json()).detail ?? `Request failed (${response.status})`);
  return response.json();
}

export async function analyzeVideo(file: File, caption: string, audience: string): Promise<AnalyzeResult> {
  // FormData is how browsers send files: like a form with an attachment.
  const form = new FormData();
  form.append("file", file);
  form.append("caption", caption);
  form.append("audience", audience);
  const response = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: form });
  if (!response.ok) throw new Error((await response.json()).detail ?? `Upload failed (${response.status})`);
  return response.json();
}

/** Start a simulation and call `onEvent` for each event as it arrives. Returns a function that stops it. */
export function streamSimulation(params: Record<string, string>, onEvent: (event: SimulationEvent) => void): () => void {
  // EventSource keeps a connection open and receives the server's events one by one.
  const source = new EventSource(`${API_URL}/api/simulate?${new URLSearchParams(params)}`);
  source.onmessage = (message) => {
    const event: SimulationEvent = JSON.parse(message.data);
    onEvent(event);
    // Close it ourselves: otherwise the browser would reconnect and start a new simulation.
    if (event.type === "done" || event.type === "error") source.close();
  };
  source.onerror = () => {
    source.close();
    onEvent({ type: "error", message: "Lost the connection to the Viralyst API." });
  };
  return () => source.close();
}
