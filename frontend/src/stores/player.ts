import { create } from "zustand";
import type { Reaction, Segment } from "@/lib/types";

export type PlayerStatus =
  | "idle" | "loading" | "ready" | "playing" | "paused" | "buffering" | "interrupted" | "completed" | "failed";

/** UI-facing playback state. Updated by the controller only when values change. */
interface PlayerState {
  status: PlayerStatus;
  error: string | null;
  loaded: number;
  toLoad: number;
  sceneKey: string | null;
  sceneTitle: string;
  queueKind: "scene" | "response" | null;
  segIndex: number;
  segment: Segment | null;
  wordIndex: number;
  position: number;
  duration: number;
  reactions: Record<string, Reaction>;
  evidenceId: string | null;
  burst: number; // increments to trigger the OBJECTION! burst
  titleCard: { phase: string; title: string } | null;
  verdictStamp: boolean;
  volume: number;
  subtitles: boolean;
  set: (p: Partial<PlayerState>) => void;
}

export const usePlayer = create<PlayerState>((set) => ({
  status: "idle",
  error: null,
  loaded: 0,
  toLoad: 0,
  sceneKey: null,
  sceneTitle: "",
  queueKind: null,
  segIndex: -1,
  segment: null,
  wordIndex: -1,
  position: 0,
  duration: 0,
  reactions: {},
  evidenceId: null,
  burst: 0,
  titleCard: null,
  verdictStamp: false,
  volume: 0.9,
  subtitles: true,
  set: (p) => set(p),
}));
