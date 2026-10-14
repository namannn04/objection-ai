import type { CharacterInfo } from "./types";

const v = (kind: "human" | "object", palette: string, glyph = "", accessory = "none") => ({ kind, palette, glyph, accessory });

/** The recurring ensemble plus the showcase defendant/witness — used for decorative previews. */
export const DEMO_CAST: CharacterInfo[] = [
  { key: "judge", role: "judge", name: "Judge Augustus Gravel", title: "The Honorable", personality: "Extremely serious. Secretly delighted by chaos.", relationship: "", visual: v("human", "gold", "", "wig"), surprise: false, voice: null },
  { key: "prosecutor", role: "prosecutor", name: "Victoria Vex", title: "Prosecutor", personality: "Treats tiny inconveniences as crimes against humanity.", relationship: "", visual: v("human", "burgundy", "", "glasses"), surprise: false, voice: null },
  { key: "defense", role: "defense", name: "Felix Loophole", title: "Defense Attorney", personality: "Finds loopholes nobody asked for.", relationship: "", visual: v("human", "teal", "", "bowtie"), surprise: false, voice: null },
  { key: "reporter", role: "reporter", name: "Penny Quill", title: "Court Reporter", personality: "Narrates like a nature documentary.", relationship: "", visual: v("human", "ivory", "", "headset"), surprise: false, voice: null },
  { key: "defendant", role: "defendant", name: "JavaScript", title: "The Defendant", personality: "Convinced every bug is a feature.", relationship: "", visual: v("object", "gold", "JS"), surprise: false, voice: null },
  { key: "witness_1", role: "witness", name: "TypeScript", title: "Witness", personality: "JavaScript in a blazer.", relationship: "", visual: v("object", "violet", "TS"), surprise: false, voice: null },
];

export const DEMO_LINES: { speaker: string; emotion: string; text: string }[] = [
  { speaker: "judge", emotion: "deadpan", text: "I have been a judge for thirty-one years. I have never wanted to retire more." },
  { speaker: "defendant", emotion: "amused", text: "I'd like to plead not guilty. Or… undefined. Whichever one doesn't throw." },
  { speaker: "judge", emotion: "stern", text: "The defendant will pick a type and commit to it." },
  { speaker: "prosecutor", emotion: "dramatic", text: "The string 'one', plus the number one. It equals eleven, Your Honor. Eleven." },
  { speaker: "defense", emotion: "angry", text: "Objection! The prosecution is leading the court into arithmetic!" },
  { speaker: "judge", emotion: "stern", text: "Overruled. Arithmetic is exactly where we lead people in this courtroom." },
  { speaker: "witness_1", emotion: "desperate", text: "Deep down, I am JavaScript! I'm just JavaScript wearing a blazer!" },
];
