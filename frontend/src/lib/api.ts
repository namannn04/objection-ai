import type {
  CaseDetail, CaseSummary, Estimate, Job, Manifest, Mode, SessionState, SettingsInfo, Usage, Verdict,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export const mediaUrl = (path: string) => (path.startsWith("http") ? path : `${API_URL}${path}`);

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError(0, "The courthouse is unreachable. Is the backend running on " + API_URL + "?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export interface NewCase {
  defendant: string;
  accusation: string;
  context?: string;
  language?: string;
  comedy_intensity: "mild" | "unserious" | "chaos";
  drama_level: number;
  trial_length: "quick" | "standard" | "full";
  participation_mode: Mode;
}

export const api = {
  listCases: (params: { showcase?: boolean; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.showcase !== undefined) q.set("showcase", String(params.showcase));
    if (params.limit) q.set("limit", String(params.limit));
    return request<CaseSummary[]>(`/api/cases?${q}`);
  },
  createCase: (body: NewCase) => post<{ case: CaseSummary; job_id: string }>("/api/cases", body),
  getCase: (ref: string) => request<CaseDetail>(`/api/cases/${ref}`),
  status: (ref: string) => request<{ status: string; detail: string; title: string; job: Job | null }>(`/api/cases/${ref}/status`),
  regenerate: (ref: string) => post<Job>(`/api/cases/${ref}/prepare`),
  manifest: (ref: string) => request<Manifest>(`/api/cases/${ref}/manifest`),
  estimate: (ref: string, provider?: string) =>
    request<Estimate>(`/api/cases/${ref}/audio/estimate${provider ? `?provider=${provider}` : ""}`),
  prepareAudio: (ref: string, provider: "mock" | "fish-free") => post<Job>(`/api/cases/${ref}/audio/prepare`, { provider }),
  authorizeAudio: (ref: string, expected_cost_usd: number, allow_reserve = false) =>
    post<Job>(`/api/cases/${ref}/audio/authorize`, { confirm: "SPEND CREDITS", expected_cost_usd, allow_reserve }),
  openSession: (ref: string, mode?: Mode) =>
    post<{ state: SessionState; manifest: Manifest }>(`/api/cases/${ref}/sessions`, { mode }),
  session: (id: string) => request<SessionState>(`/api/sessions/${id}`),
  start: (id: string) => post<SessionState>(`/api/sessions/${id}/start`),
  completeScene: (id: string, scene: string) => post<SessionState>(`/api/sessions/${id}/scenes/${scene}/complete`),
  choose: (id: string, scene: string, option_id: string) =>
    post<{ state: SessionState; intervention_id: string; response_turn_keys: string[] }>(
      `/api/sessions/${id}/windows/${scene}/choose`, { option_id }),
  intervene: (id: string, scene: string, text: string) =>
    post<{ state: SessionState; intervention_id: string; job_id?: string; status: string }>(
      `/api/sessions/${id}/windows/${scene}/intervene`, { text }),
  resolve: (id: string) => post<SessionState>(`/api/sessions/${id}/windows/resolve`),
  verdict: (id: string) => request<Verdict>(`/api/sessions/${id}/verdict`),
  replay: (id: string, mode?: Mode) => post<{ state: SessionState; manifest: Manifest }>(`/api/sessions/${id}/replay`, { mode }),
  settings: () => request<SettingsInfo>("/api/settings"),
  patchSettings: (body: { default_llm_provider?: string; default_audio_provider?: string }) =>
    request<SettingsInfo>("/api/settings", { method: "PATCH", body: JSON.stringify(body) }),
  usage: () => request<Usage>("/api/usage"),
  refreshBalance: () => post<{ credit: string }>("/api/usage/balance/refresh"),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  createPodcast: (ref: string, body: { verdict?: "guilty" | "not_guilty"; session_id?: string }) =>
    post<{ id: string; job_id: string; status: string }>(`/api/cases/${ref}/podcast`, body),
  podcast: (id: string) => request<Podcast>(`/api/podcasts/${id}`),
  casePodcasts: (ref: string) => request<Podcast[]>(`/api/cases/${ref}/podcasts`),
};

export interface Podcast {
  id: string;
  case_id: string;
  title: string;
  status: string;
  mp3_url: string | null;
  wav_url: string | null;
  duration_ms: number;
  chapters: { title: string; start_ms: number; phase: string }[];
  transcript: { turn_key: string; speaker: string; name: string; text: string; start_ms: number; end_ms: number }[];
  verdict: "guilty" | "not_guilty" | null;
  created_at: string;
}

export function eventsUrl(ref: string) {
  return `${API_URL}/api/cases/${ref}/events`;
}
