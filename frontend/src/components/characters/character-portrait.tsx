"use client";

import { AnimatePresence, motion } from "motion/react";
import type { CharacterInfo, Reaction } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { AmplitudeSource } from "./face-parts";
import { HumanPortrait } from "./human";
import { ObjectPortrait } from "./object";
import { REACTION_TO_EXPRESSION, expressionFor, type Expression } from "./palette";

const REACTION_MARK: Partial<Record<Reaction, string>> = {
  gasp: "!", shocked: "!!", confused: "?", laugh: "ha", angry: "#", sweat: "…", facepalm: "ugh", smirk: "heh", nod: "mm",
};

export interface PortraitProps {
  character: CharacterInfo;
  speaking?: boolean;
  emotion?: string;
  reaction?: Reaction | null;
  amplitude?: AmplitudeSource | null;
  dimmed?: boolean;
  className?: string;
  blinkDelay?: number;
}

/** CharacterPortrait: picks the art style, resolves expression (reaction > speaking emotion > neutral). */
export function CharacterPortrait({
  character, speaking = false, emotion, reaction, amplitude = null, dimmed = false, className, blinkDelay = 0,
}: PortraitProps) {
  const expression: Expression = reaction ? REACTION_TO_EXPRESSION[reaction] : speaking ? expressionFor(emotion) : "neutral";
  const isHuman = character.visual?.kind === "human" || ["judge", "prosecutor", "defense", "reporter"].includes(character.key);
  return (
    <div
      className={cn(
        "relative transition-[filter,opacity] duration-500 ease-[var(--ease-court)]",
        speaking && "speaking",
        dimmed ? "brightness-[0.55] saturate-[0.7]" : "brightness-100",
        className,
      )}
      style={{ "--blink-delay": `${blinkDelay}s` } as React.CSSProperties}
    >
      <motion.div
        className="h-full w-full"
        animate={reaction === "nod" ? { y: [0, 4, 0, 4, 0] } : reaction === "gasp" || reaction === "shocked" ? { y: [0, -6, 0] } : { y: 0 }}
        transition={{ duration: 0.6 }}
      >
        {isHuman ? (
          <HumanPortrait characterKey={character.key} expression={expression} speaking={speaking} amplitude={amplitude} palette={character.visual?.palette} />
        ) : (
          <ObjectPortrait
            name={character.name}
            glyph={character.visual?.glyph ?? ""}
            paletteName={character.visual?.palette ?? "slate"}
            expression={expression}
            speaking={speaking}
            amplitude={amplitude}
          />
        )}
      </motion.div>
      <AnimatePresence>
        {reaction && REACTION_MARK[reaction] && (
          <motion.span
            key={reaction}
            initial={{ opacity: 0, scale: 0.4, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.6 }}
            transition={{ type: "spring", stiffness: 420, damping: 18 }}
            className="absolute -top-1 right-[8%] rounded-full border border-gold/60 bg-ink/90 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-gold"
          >
            {REACTION_MARK[reaction]}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}
