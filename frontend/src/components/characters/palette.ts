import type { Reaction } from "@/lib/types";

export const PALETTES: Record<string, { base: string; dark: string; light: string }> = {
  gold: { base: "#c99a45", dark: "#7d5e27", light: "#efd49b" },
  burgundy: { base: "#8e2b38", dark: "#521820", light: "#c4515f" },
  ivory: { base: "#ddd5c3", dark: "#9a9282", light: "#fffaf0" },
  teal: { base: "#2f6f6a", dark: "#1a413e", light: "#5aa39c" },
  violet: { base: "#5b4a8b", dark: "#352a55", light: "#8e7cc4" },
  ember: { base: "#c2643a", dark: "#763a1f", light: "#e8936b" },
  slate: { base: "#4a5563", dark: "#2a3039", light: "#7b8796" },
  moss: { base: "#4f6b3a", dark: "#2f4122", light: "#86a66b" },
};

export const palette = (name?: string) => PALETTES[name ?? "slate"] ?? PALETTES.slate;

export type Expression = "neutral" | "surprised" | "angry" | "confused" | "laughing" | "smug" | "sad" | "nervous" | "stern";

const EMOTION_TO_EXPRESSION: Record<string, Expression> = {
  angry: "angry",
  exasperated: "angry",
  shocked: "surprised",
  confused: "confused",
  amused: "laughing",
  triumphant: "smug",
  smug: "smug",
  sarcastic: "smug",
  proud: "smug",
  sad: "sad",
  nervous: "nervous",
  desperate: "nervous",
  stern: "stern",
  serious: "stern",
  deadpan: "neutral",
  dramatic: "stern",
};

export const expressionFor = (emotion?: string): Expression => EMOTION_TO_EXPRESSION[emotion ?? ""] ?? "neutral";

export const REACTION_TO_EXPRESSION: Record<Reaction, Expression> = {
  gasp: "surprised",
  shocked: "surprised",
  facepalm: "angry",
  smirk: "smug",
  angry: "angry",
  confused: "confused",
  laugh: "laughing",
  nod: "neutral",
  sweat: "nervous",
};
