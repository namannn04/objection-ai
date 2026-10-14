"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";
import type { Manifest, Mode, Verdict } from "@/lib/types";
import { cn, formatMs } from "@/lib/utils";
import { usePlayer } from "@/stores/player";

/** The stamp: lands right after the judge says the word. Reduced motion → simple fade. */
export function VerdictReveal({ verdict }: { verdict: Verdict | null }) {
  const stamp = usePlayer((s) => s.verdictStamp);
  const status = usePlayer((s) => s.status);
  return (
    <AnimatePresence>
      {stamp && verdict && status !== "completed" && (
        <motion.div className="pointer-events-none absolute inset-0 z-20 grid place-items-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <motion.div
            initial={{ scale: 2.6, rotate: -14, opacity: 0 }}
            animate={{ scale: 1, rotate: -8, opacity: 1 }}
            transition={{ type: "spring", stiffness: 380, damping: 20 }}
            className={cn("rounded-lg border-[6px] px-8 py-3 font-display text-[clamp(3rem,10vw,8rem)] uppercase leading-none tracking-tight mix-blend-screen",
              verdict.guilty ? "border-burgundy-bright text-burgundy-bright" : "border-[#5aa39c] text-[#5aa39c]")}
          >
            {verdict.guilty ? "Guilty" : "Not guilty"}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

const HIGHLIGHT_LABEL: Record<string, string> = {
  funniest_objection: "Funniest objection",
  best_comeback: "Best ruling",
  most_dramatic: "Most dramatic statement",
  most_unexpected: "Most unexpected testimony",
};

export function VerdictCard({ verdict, manifest, mode, startedAt, onReplay }: {
  verdict: Verdict; manifest: Manifest; mode: Mode; startedAt: number; onReplay: (m?: Mode) => void;
}) {
  const [copied, setCopied] = useState(false);
  const name = (k: string) => manifest.characters.find((c) => c.key === k)?.name ?? k;
  const jury = verdict.scoreboard.jury;
  const duration = Date.now() - startedAt;
  const share = async () => {
    const url = `${window.location.origin}/case/${manifest.case.slug}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.prompt("Copy this link", url);
    }
  };
  return (
    <motion.div
      className="fixed inset-0 z-50 overflow-y-auto bg-ink/[0.97] backdrop-blur-md"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-8 sm:py-20">
        <div className="font-mono text-[11px] tracking-[0.2em] text-mute">{manifest.case.case_number} · {manifest.case.title.toUpperCase()}</div>
        <motion.h2
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className={cn("mt-6 font-display text-[clamp(2.8rem,8vw,7rem)] leading-[0.88] text-balance", verdict.guilty ? "text-ivory" : "text-ivory")}
        >
          {verdict.guilty ? <>Guilty of <span className="italic text-burgundy-bright">{verdict.headline.replace(/^GUILTY OF /, "").toLowerCase()}</span>.</> : <>Not guilty. <span className="italic text-[#5aa39c]">Reluctantly.</span></>}
        </motion.h2>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="mt-10 grid gap-8 md:grid-cols-[1.4fr_1fr]">
          <div>
            <div className="eyebrow">{verdict.guilty ? "The sentence" : "The ruling"}</div>
            <p className="mt-3 font-display text-3xl leading-snug">{verdict.sentence}</p>
            <div className="eyebrow mt-8">The court’s reasoning</div>
            <p className="mt-3 text-ivory-dim">{verdict.reasoning}</p>
          </div>
          <div className="grid grid-cols-2 gap-px self-start overflow-hidden rounded-2xl border hairline bg-line">
            <Stat k="Jury" v={`${jury.guilty}–${jury.not_guilty}`} sub={`${jury.simulated} simulated jurors${jury.guilty + jury.not_guilty > jury.simulated ? " + you" : ""}`} />
            <Stat k="Session" v={formatMs(duration)} sub="time in court" />
            <Stat k="The People" v={String(verdict.scoreboard.board.prosecution)} sub="points on the record" />
            <Stat k="The Defense" v={String(verdict.scoreboard.board.defense)} sub="points on the record" />
          </div>
        </motion.div>
        <div className="mt-14">
          <div className="eyebrow">Courtroom highlights</div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {Object.entries(verdict.highlights).filter(([, h]) => h).map(([k, h]) => (
              <figure key={k} className="rounded-2xl border hairline bg-ink-2 p-5">
                <figcaption className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold">{HIGHLIGHT_LABEL[k] ?? k} · {name(h!.speaker)}</figcaption>
                <blockquote className="mt-2 font-display text-xl leading-snug">“{h!.text}”</blockquote>
              </figure>
            ))}
          </div>
        </div>
        <div className="mt-14 flex flex-wrap items-center gap-3">
          <button onClick={() => onReplay(mode)} className="rounded-full bg-gold px-6 py-3 font-semibold text-ink">Retry with a different verdict</button>
          <Link href={`/podcast/${manifest.case.slug}`} className="rounded-full border border-line-strong px-6 py-3 hover:bg-white/5">Listen as a podcast</Link>
          <button onClick={share} className="rounded-full border border-line-strong px-6 py-3 hover:bg-white/5">{copied ? "Link copied" : "Copy share link"}</button>
          <Link href="/file" className="ml-auto font-mono text-[11px] uppercase tracking-[0.18em] text-mute hover:text-ivory">File another case →</Link>
        </div>
      </div>
    </motion.div>
  );
}

function Stat({ k, v, sub }: { k: string; v: string; sub: string }) {
  return (
    <div className="bg-ink-2 p-5">
      <div className="eyebrow">{k}</div>
      <div className="mt-2 font-display text-4xl">{v}</div>
      <div className="mt-1 text-xs text-mute">{sub}</div>
    </div>
  );
}
