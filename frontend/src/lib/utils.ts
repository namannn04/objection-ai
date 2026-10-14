import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMs(ms: number) {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export const PHASE_LABEL: Record<string, string> = {
  CASE_CREATED: "Filed",
  CASE_PREPARATION: "Preparing",
  SCRIPT_PLANNING: "Writing the trial",
  SCRIPT_VALIDATION: "Checking the record",
  AUDIO_PREPARATION: "Recording voices",
  COURTROOM_READY: "Ready for trial",
  OPENING_STATEMENTS: "Opening statements",
  EVIDENCE_PRESENTATION: "Evidence",
  WITNESS_EXAMINATION: "Witness examination",
  CROSS_EXAMINATION: "Cross-examination",
  PLAYER_INTERVENTION: "The jury speaks",
  CLOSING_ARGUMENTS: "Closing arguments",
  DELIBERATION: "Deliberation",
  VERDICT: "Verdict",
  CASE_COMPLETED: "Case closed",
  FAILED: "Mistrial",
};

export const ROLE_LABEL: Record<string, string> = {
  judge: "The Bench",
  prosecutor: "For the People",
  defense: "For the Defense",
  defendant: "The Defendant",
  witness: "Witness",
  reporter: "Court Reporter",
};
