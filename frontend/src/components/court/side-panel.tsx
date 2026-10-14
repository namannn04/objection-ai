"use client";

import { useState } from "react";
import { EvidenceCard } from "@/components/case/evidence-card";
import type { Manifest, SessionState } from "@/lib/types";
import { cn } from "@/lib/utils";
import { usePlayer } from "@/stores/player";

/** Live "scales": tally of points scored so far in the record (lines + jury input). */
function useScales(manifest: Manifest, session: SessionState | null) {
  const sceneKey = usePlayer((s) => s.sceneKey);
  const segIndex = usePlayer((s) => s.segIndex);
  const board = { prosecution: 0, defense: 0 };
  const order = manifest.scenes.filter((s) => !s.branch);
  const current = order.findIndex((s) => s.key === sceneKey);
  order.forEach((sc, i) => {
    sc.segments.forEach((seg, j) => {
      const heard = i < current || (i === current && j <= segIndex);
      if (heard && seg.scores && seg.points) board[seg.scores] += seg.points;
    });
  });
  for (const iv of session?.interventions ?? []) {
    const sc = manifest.scenes.find((s) => s.key === iv.scene);
    const opt = sc?.window?.options.find((o) => o.id === iv.option_id);
    if (opt?.favours) board[opt.favours] += opt.points;
  }
  return board;
}

export function SidePanel({ manifest, session }: { manifest: Manifest; session: SessionState | null }) {
  const [tab, setTab] = useState<"evidence" | "notes" | "jury">("evidence");
  const evidenceId = usePlayer((s) => s.evidenceId);
  const sceneKey = usePlayer((s) => s.sceneKey);
  const order = manifest.scenes.map((s) => s.key);
  const presented = new Set<string>();
  const curIdx = order.indexOf(sceneKey ?? "");
  manifest.scenes.forEach((sc, i) => {
    if (i <= curIdx) sc.segments.forEach((seg) => seg.evidence_id && presented.add(seg.evidence_id));
  });
  if (evidenceId) presented.add(evidenceId);
  const board = useScales(manifest, session);
  const total = board.prosecution + board.defense || 1;
  const tilt = ((board.prosecution - board.defense) / total) * 12;

  return (
    <aside className="flex h-full flex-col rounded-2xl border hairline bg-ink-2">
      <div className="flex border-b hairline p-1.5" role="tablist">
        {(["evidence", "notes", "jury"] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={cn("flex-1 rounded-lg py-2 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors",
              tab === t ? "bg-ink-3 text-ivory" : "text-mute hover:text-ivory")}>
            {t === "jury" ? "Jury" : t === "notes" ? "Case notes" : "Evidence"}
          </button>
        ))}
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {tab === "evidence" && manifest.evidence.map((e) => (
          <EvidenceCard key={e.id} e={e} compact active={evidenceId === e.id} revealed={!e.is_twist || presented.has(e.id)} />
        ))}
        {tab === "notes" && (
          <div className="space-y-5 text-sm">
            <div>
              <div className="eyebrow">The accusation</div>
              <p className="mt-2 text-ivory-dim">{manifest.case.accusation}</p>
            </div>
            <div>
              <div className="eyebrow">In the courtroom</div>
              <ul className="mt-2 space-y-2">
                {manifest.characters.filter((c) => !c.surprise || presentedSurprise(manifest, sceneKey, c.key)).map((c) => (
                  <li key={c.key}>
                    <span className="text-ivory">{c.name}</span>
                    <span className="text-mute"> — {c.personality}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="eyebrow">Voices</div>
              <p className="mt-2 text-mute">{manifest.audio.providers.join(", ") === "mock" ? "Local procedural mock voices (no paid credits)." : `Recorded with: ${manifest.audio.providers.join(", ")}`}</p>
            </div>
          </div>
        )}
        {tab === "jury" && (
          <div>
            <div className="eyebrow">The scales, so far</div>
            <svg viewBox="0 0 200 120" className="mx-auto mt-4 w-full max-w-[240px]" aria-label={`Prosecution ${board.prosecution}, defense ${board.defense}`}>
              <line x1="100" y1="18" x2="100" y2="108" stroke="#d6ae62" strokeWidth="2" />
              <line x1="70" y1="110" x2="130" y2="110" stroke="#d6ae62" strokeWidth="2" />
              <g style={{ transform: `rotate(${tilt}deg)`, transformOrigin: "100px 24px", transition: "transform 900ms cubic-bezier(.22,1,.36,1)" }}>
                <line x1="30" y1="24" x2="170" y2="24" stroke="#d6ae62" strokeWidth="2.5" />
                <path d="M30 24 L16 62 L44 62 Z M170 24 L156 62 L184 62 Z" fill="none" stroke="#d6ae62" strokeWidth="1.2" />
                <ellipse cx="30" cy="64" rx="18" ry="5" fill="#c4515f" opacity="0.8" />
                <ellipse cx="170" cy="64" rx="18" ry="5" fill="#5aa39c" opacity="0.8" />
              </g>
            </svg>
            <div className="mt-4 grid grid-cols-2 gap-2 text-center">
              <div className="rounded-xl border border-[#c4515f]/40 p-3"><div className="font-display text-3xl">{board.prosecution}</div><div className="eyebrow">The People</div></div>
              <div className="rounded-xl border border-[#5aa39c]/40 p-3"><div className="font-display text-3xl">{board.defense}</div><div className="eyebrow">The Defense</div></div>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-mute">Points from arguments heard so far and your interventions. The verdict also weighs the evidence — and your final vote counts for a lot.</p>
            {!!session?.votes.length && (
              <ul className="mt-4 space-y-1 text-sm text-ivory-dim">
                {session.votes.map((v) => <li key={v.scene}>Your vote: <span className="text-gold">{v.choice}</span></li>)}
              </ul>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

function presentedSurprise(m: Manifest, sceneKey: string | null, key: string) {
  const idx = m.scenes.findIndex((s) => s.key === sceneKey);
  return m.scenes.some((s, i) => i <= idx && s.segments.some((seg) => seg.speaker === key));
}
