"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import type { InterventionWindow, Mode } from "@/lib/types";
import { cn } from "@/lib/utils";
import { usePlayer } from "@/stores/player";

/** The big satisfying button. Live only inside an objection window; cannot be spammed. */
export function ObjectionButton({ armed, onPress, mode }: { armed: boolean; onPress: () => void; mode: Mode }) {
  const [cool, setCool] = useState(false);
  if (mode === "spectator") return null;
  return (
    <button
      onClick={() => {
        if (!armed || cool) return;
        setCool(true);
        setTimeout(() => setCool(false), 1500);
        onPress();
      }}
      disabled={!armed || cool}
      title={armed ? "Object!" : "The court isn't taking objections right now"}
      className={cn(
        "group relative flex w-full items-center justify-center gap-3 overflow-hidden rounded-2xl border px-5 py-4 font-display text-3xl italic transition-all",
        armed ? "animate-pulse-gold border-burgundy-bright bg-burgundy text-ivory hover:-translate-y-0.5" : "cursor-not-allowed border-line bg-ink-3 text-mute",
      )}
    >
      Objection!
      {!armed && <span className="absolute bottom-1 font-sans text-[10px] not-italic tracking-wider text-mute/70">waiting for an opening</span>}
    </button>
  );
}

export function InterventionPanel({ window: w, mode, onChoose, onSkip, onFreeText }: {
  window: InterventionWindow; mode: Mode; onChoose: (id: string) => void; onSkip: () => void; onFreeText: (t: string) => void;
}) {
  const [revealed, setRevealed] = useState(w.kind !== "objection");
  const [text, setText] = useState("");
  const status = usePlayer((s) => s.status);
  const busy = status === "buffering";
  const isFinal = w.kind === "vote" && w.options.some((o) => o.points >= 6);

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-2xl border border-gold/40 bg-ink-2/95 p-5 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9)] backdrop-blur sm:p-6"
      role="dialog"
      aria-label="Jury intervention"
    >
      <div className="flex items-center justify-between">
        <div className="eyebrow text-gold">{w.kind === "vote" ? (isFinal ? "The final vote" : "Jury vote") : w.kind === "objection" ? "Objection window" : "The jury may ask"}</div>
        <button onClick={onSkip} disabled={busy} className="font-mono text-[10px] uppercase tracking-[0.18em] text-mute hover:text-ivory">
          {w.kind === "vote" ? "Abstain" : "Let it go"} →
        </button>
      </div>
      <h3 className="mt-2 font-display text-3xl leading-tight sm:text-4xl">{w.prompt}</h3>

      {!revealed ? (
        <div className="mt-5 max-w-sm">
          <ObjectionButton armed mode={mode} onPress={() => setRevealed(true)} />
        </div>
      ) : (
        <AnimatePresence>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={cn("mt-5 grid gap-3", w.options.length === 2 && "sm:grid-cols-2")}>
            {w.options.map((o) => (
              <button
                key={o.id}
                disabled={busy}
                onClick={() => onChoose(o.id)}
                className={cn(
                  "group rounded-xl border p-4 text-left transition-all hover:-translate-y-0.5 disabled:opacity-50",
                  w.kind === "vote" && o.favours === "prosecution" ? "border-[#c4515f]/50 hover:bg-[#c4515f]/10" :
                    w.kind === "vote" && o.favours === "defense" ? "border-[#5aa39c]/50 hover:bg-[#5aa39c]/10" : "border-line-strong hover:border-gold hover:bg-gold/5",
                )}
              >
                <div className={cn("font-display text-2xl", w.kind === "vote" ? "" : "italic text-gold")}>{o.label}</div>
                <div className="mt-1 text-sm text-ivory-dim">{o.text}</div>
              </button>
            ))}
          </motion.div>
        </AnimatePresence>
      )}

      {mode === "chaos" && w.allow_free_text && revealed && (
        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim().length >= 3) onFreeText(text.trim());
          }}
        >
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={240}
            placeholder="Objection! I demand to see the defendant's browsing history."
            className="min-w-0 flex-1 rounded-xl border border-line-strong bg-ink px-4 py-3 text-sm text-ivory placeholder:text-mute/60 focus:border-gold focus:outline-none"
            aria-label="Your own intervention"
          />
          <button disabled={busy || text.trim().length < 3} className="rounded-xl bg-burgundy px-4 py-3 font-semibold text-ivory disabled:opacity-40">
            {busy ? "…" : "Shout it"}
          </button>
        </form>
      )}
      {mode === "chaos" && revealed && <p className="mt-2 text-xs text-mute">Free-text interventions are written live by the agents; voices follow your audio settings.</p>}
    </motion.div>
  );
}
