"use client";

import { CharacterPortrait } from "@/components/characters/character-portrait";
import type { CharacterInfo } from "@/lib/types";
import { ROLE_LABEL } from "@/lib/utils";

export function WitnessCard({ c, i = 0 }: { c: CharacterInfo; i?: number }) {
  return (
    <div className="flex gap-4 rounded-2xl border hairline bg-ink-2 p-4">
      <div className="relative h-24 w-20 shrink-0 overflow-hidden rounded-xl bg-[radial-gradient(circle_at_50%_30%,#2a2420,#121110)]">
        <div className="absolute inset-x-0 bottom-0 top-[6%]"><CharacterPortrait character={c} blinkDelay={i * 0.9} className="h-full w-full" /></div>
      </div>
      <div className="min-w-0">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold">
          {c.surprise ? "Surprise witness" : c.title || ROLE_LABEL[c.role]}
        </div>
        <div className="mt-1 font-medium leading-tight">{c.name}</div>
        <p className="mt-1.5 line-clamp-3 text-sm leading-snug text-mute">{c.relationship || c.personality}</p>
      </div>
    </div>
  );
}
