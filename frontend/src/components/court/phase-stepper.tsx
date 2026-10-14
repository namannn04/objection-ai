"use client";

import type { Manifest, SessionState } from "@/lib/types";
import { cn } from "@/lib/utils";
import { usePlayer } from "@/stores/player";

const STEPS: { phase: string; label: string }[] = [
  { phase: "OPENING_STATEMENTS", label: "Opening" },
  { phase: "EVIDENCE_PRESENTATION", label: "Evidence" },
  { phase: "WITNESS_EXAMINATION", label: "Witness" },
  { phase: "CROSS_EXAMINATION", label: "Cross" },
  { phase: "CLOSING_ARGUMENTS", label: "Closing" },
  { phase: "DELIBERATION", label: "Deliberation" },
  { phase: "VERDICT", label: "Verdict" },
];

/** Where we are in the trial — a court docket, not a video timeline. */
export function PhaseStepper({ manifest, session }: { manifest: Manifest; session: SessionState | null }) {
  const sceneKey = usePlayer((s) => s.sceneKey);
  const scenePhase = manifest.scenes.find((s) => s.key === sceneKey)?.phase;
  const present = new Set(manifest.scenes.map((s) => s.phase));
  const steps = STEPS.filter((s) => present.has(s.phase as never));
  const phase = session?.phase === "PLAYER_INTERVENTION" ? scenePhase : session?.phase === "CASE_COMPLETED" ? "DONE" : session?.phase;
  const at = phase === "DONE" ? steps.length : steps.findIndex((s) => s.phase === phase);
  return (
    <ol className="flex w-full items-center gap-1.5 sm:gap-2" aria-label="Trial progress">
      {steps.map((s, i) => {
        const done = at > i;
        const now = at === i;
        return (
          <li key={s.phase} className="flex min-w-0 flex-1 flex-col gap-1.5">
            <span className={cn("h-[3px] rounded-full transition-colors duration-700", done ? "bg-gold" : now ? "bg-gold/60" : "bg-ink-4")} />
            <span className={cn("truncate font-mono text-[9px] uppercase tracking-[0.16em] sm:text-[10px]",
              now ? "text-gold" : done ? "text-ivory-dim" : "text-mute/60")}>
              {now && <span className="mr-1 inline-block h-1.5 w-1.5 animate-blink rounded-full bg-burgundy-bright align-middle" />}
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
