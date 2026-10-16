export type Phase =
  | "CASE_CREATED" | "CASE_PREPARATION" | "SCRIPT_PLANNING" | "SCRIPT_VALIDATION" | "AUDIO_PREPARATION"
  | "COURTROOM_READY" | "OPENING_STATEMENTS" | "EVIDENCE_PRESENTATION" | "WITNESS_EXAMINATION"
  | "CROSS_EXAMINATION" | "PLAYER_INTERVENTION" | "CLOSING_ARGUMENTS" | "DELIBERATION" | "VERDICT"
  | "CASE_COMPLETED" | "FAILED";

export type Mode = "spectator" | "jury" | "chaos";
export type Side = "prosecution" | "defense";
export type Role = "judge" | "prosecutor" | "defense" | "defendant" | "witness" | "reporter";
export type Reaction = "gasp" | "facepalm" | "smirk" | "angry" | "confused" | "laugh" | "shocked" | "nod" | "sweat";
export type Sfx = "gavel" | "objection" | "crowd_gasp" | "crowd_laugh" | "crowd_murmur" | "dramatic_sting";

export interface CaseSummary {
  id: string;
  slug: string;
  title: string;
  case_number: string;
  defendant: string;
  accusation: string;
  status: Phase;
  status_detail: string;
  trial_length: "quick" | "standard" | "full";
  participation_mode: Mode;
  comedy_intensity: "mild" | "unserious" | "chaos";
  drama_level: number;
  is_showcase: boolean;
  is_featured: boolean;
  llm_provider: string;
  audio_provider: string;
  paid_audio_authorized: boolean;
  created_at: string;
}

export interface Visual {
  kind: "human" | "object" | "concept";
  glyph: string;
  palette: string;
  accessory: string;
  hair?: string | null;
  mustache?: boolean;
  attire?: "suit" | "saree";
  bindi?: boolean;
}

export interface CharacterInfo {
  key: string;
  role: Role;
  name: string;
  title: string;
  personality: string;
  relationship: string;
  visual: Visual;
  surprise: boolean;
  voice: { label: string; direction: string } | null;
}

export interface Evidence {
  id: string;
  title: string;
  description: string;
  kind: string;
  favours: Side;
  strength: number;
  details: string[];
  is_twist: boolean;
}

export interface WordTiming {
  w: string;
  s: number;
  e: number;
}

export interface Segment {
  turn_key: string;
  speaker: string;
  kind: string;
  text: string;
  subtitle: string;
  emotion: string;
  delivery: string;
  intensity: number;
  reactions: Record<string, Reaction>;
  evidence_id: string | null;
  technique: string | null;
  scores: Side | null;
  points: number;
  gap_before_ms: number;
  sfx_before: Sfx[];
  sfx_after: Sfx[];
  audio: {
    url: string;
    duration_ms: number;
    provider: string;
    model: string;
    words: WordTiming[];
    timing_source: "exact" | "estimated";
  } | null;
}

export interface WindowOption {
  id: string;
  label: string;
  text: string;
  favours: Side | null;
  points: number;
  response: Segment[];
}

export interface InterventionWindow {
  kind: "objection" | "question" | "vote";
  prompt: string;
  allow_free_text: boolean;
  options: WindowOption[];
}

export interface Scene {
  key: string;
  order: number;
  phase: Phase;
  title: string;
  branch: "verdict_guilty" | "verdict_not_guilty" | null;
  humor_score: number | null;
  segments: Segment[];
  window: InterventionWindow | null;
  live_branches: Record<string, Segment[]>;
}

export interface Manifest {
  case: {
    id: string; slug: string; title: string; case_number: string; defendant: string; accusation: string;
    status: Phase; participation_mode: Mode; trial_length: string; drama_level: number; is_showcase: boolean; version: number;
  };
  characters: CharacterInfo[];
  evidence: Evidence[];
  scenes: Scene[];
  sfx: Record<Sfx, string>;
  audio: { ready: boolean; missing: string[]; providers: string[]; estimated_main_duration_ms: number };
}

export interface Verdict {
  guilty: boolean;
  headline: string;
  reasoning: string;
  sentence: string;
  scoreboard: {
    board: Record<Side, number>;
    lines: { source: string; side: Side; points: number; turn?: string; exhibit?: string; scene?: string }[];
    jury: { guilty: number; not_guilty: number; simulated: number };
  };
  highlights: Record<string, { turn_key: string; speaker: string; text: string; scene: string } | null>;
}

export interface SessionState {
  session_id: string;
  phase: Phase;
  mode: Mode;
  cursor: number;
  next_scene: string | null;
  open_window: string | null;
  verdict_scene: string | null;
  verdict: Verdict | null;
  history: { from: string; to: string; at: string }[];
  votes: { scene: string; choice: Side }[];
  interventions: {
    id: string; scene: string; kind: string; option_id: string | null; free_text: string | null;
    status: string; source: string; response_turn_keys: string[];
  }[];
}

export interface Job {
  id: string;
  kind: string;
  status: "queued" | "running" | "done" | "failed" | "blocked";
  progress: Record<string, unknown>;
  result: Record<string, unknown>;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface CaseDetail {
  case: CaseSummary;
  plan: null | {
    title: string; case_number: string; accusation_summary: string; charges: string[]; defendant_profile: string;
    prosecutor_strategy: string; defense_strategy: string; running_gags: string[];
    punishments: { guilty: string; not_guilty: string };
    outline: { phase: Phase; goal: string; beats: string[]; techniques: string[] }[];
  };
  characters: null | (Omit<CharacterInfo, "voice" | "relationship"> & { speaking_style: string; relationship_to_case: string })[];
  evidence: Evidence[] | null;
  humor_report: null | { scenes: { scene_id: string; overall: number; notes: string[]; attempts: number; source: string }[] };
  validation: null | { valid: boolean; errors: string[]; warnings: string[]; stats: Record<string, unknown> };
  generator: string | null;
  versions: number;
}

export interface Estimate {
  provider: string;
  model: string;
  billable: boolean;
  lines: number;
  cached_lines: number;
  characters_to_generate: number;
  estimated_cost_usd: number;
  price_basis: string;
  limits: {
    max_characters_per_case: number; case_characters_spent: number; max_projected_spend_usd: number;
    projected_spend_so_far_usd: number; total_billable_characters: number; demo_reserve_usd: number;
  };
  verified_balance_usd: number | null;
  provider_available: boolean;
  provider_reason: string;
  authorized: boolean;
  note: string;
}

export interface ProviderStatus {
  available: boolean;
  billable?: boolean;
  model?: string;
  reason?: string;
}

export interface SettingsInfo {
  providers: { audio: Record<string, ProviderStatus>; llm: Record<string, ProviderStatus> };
  defaults: { llm: string; audio: string };
  paid_tts_armed: boolean;
}

export interface Usage {
  billable_characters: number;
  estimated_spend_usd: number;
  ceiling_usd: number;
  remaining_under_ceiling_usd: number;
  demo_reserve_usd: number;
  verified_balance_usd: number | null;
  verified_balance_checked_at: string | null;
  outcomes: Record<string, number>;
  records: {
    at: string; case_id: string | null; provider: string; model: string; characters: number;
    estimated_cost_usd: number; outcome: string; detail: string; billable: boolean;
  }[];
  note: string;
}
