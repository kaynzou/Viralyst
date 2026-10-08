// The shapes of the data the Python API sends. TypeScript checks we use them correctly.

export type Signal = "watch" | "share" | "save" | "comment" | "like" | "follow";

export type Status = {
  ai_available: boolean; // the server has a Claude API key
  ai_locked: boolean; // the server wants an access code for AI features
  ai_unlocked: boolean; // ...and this browser sent the right one (always true locally)
  budget: { limit: number | null; spent_today: number } | null;
  ffmpeg_available: boolean;
  models: string[];
  default_model: string;
};

export type Analysis = {
  source: string;
  analyzed_on: string;
  model: string;
  transcript: string;
  strengths: string[];
  weaknesses: string[];
  better_hook: string;
  suggested_caption: string;
};

export type VideoOption = {
  id: string;
  title: string;
  hook: string;
  length_seconds: number;
  uploaded: boolean;
  audience: string | null;
  analysis: Analysis | null;
};

export type AudienceOption = {
  id: string;
  description: string;
  interests: string[];
  kinds_of_people: number;
};

export type Examples = { videos: VideoOption[]; audiences: AudienceOption[] };

export type Reaction = {
  name: string;
  age: number;
  occupation: string;
  location: string;
  interests: string[];
  moment: string;
  in_target: boolean;
  scrolled_past: boolean;
  watch: number;
  liked: boolean;
  commented: boolean;
  shared: boolean;
  saved: boolean;
  followed: boolean;
  thought: string;
  comment: string;
};

export type WaveInfo = { label: string; size: number; target_fraction: number; represents: number };

export type StartEvent = {
  type: "start";
  seed: number;
  agent: "rules" | "ai";
  video: { title: string; hook: string; length_seconds: number };
  waves: WaveInfo[];
};

export type WaveEvent = {
  type: "wave";
  number: number;
  label: string;
  represents: number;
  rates: Record<Signal, number>;
  score: number;
  threshold: number;
  passed: boolean;
  reactions: Reaction[];
};

export type Segment = { viewers: number; watch: number; like: number; share: number };

export type DoneEvent = {
  type: "done";
  stage: number;
  verdict: string;
  reach: number;
  scroll_rate: number;
  segments: { target?: Segment; others?: Segment };
  signals: Record<Signal, number>;
  weakest: Signal;
  tip: string;
  usage: { calls: number; reused: number; failures: number; cost: number } | null;
};

export type ErrorEvent = { type: "error"; message: string };

export type SimulationEvent = StartEvent | WaveEvent | DoneEvent | ErrorEvent;

export type Odds = {
  runs: number;
  outcomes: { stage: number; label: string; share: number }[];
  // Only present once you've calibrated against your real results (backend/calibration/README.md).
  calibration: { views_per_follower: number; videos: number; typical_miss: number } | null;
};

export type AnalyzeResult = {
  id: string;
  video: { title: string; hook: string; description: string; topics: string[]; length_seconds: number;
           hook_strength: number; quality: number; shareability: number; save_value: number };
  analysis: Analysis;
  cost: number;
};

export type CompareArm = {
  name: string;
  video: string;
  title: string;
  mean_stage: number;
  breakout_rate: number;
  breakout_low: number;
  breakout_high: number;
  odds: { stage: number; label: string; share: number }[];
};

export type Comparison = { challenger: string; difference: number; low: number; high: number; verdict: string };

export type CompareResult = { runs: number; arms: CompareArm[]; comparisons: Comparison[] };
