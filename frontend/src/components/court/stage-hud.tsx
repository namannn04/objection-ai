"use client";

import { AnimatePresence, motion } from "motion/react";
import { Captions, CaptionsOff, Pause, Play, RotateCcw, Volume2, VolumeX } from "lucide-react";
import { useEffect } from "react";
import type { CharacterInfo } from "@/lib/types";
import { cn, ROLE_LABEL } from "@/lib/utils";
import { usePlayer } from "@/stores/player";

/** Keyboard: Space play/pause, ←/→ previous/next line, R replay line. */
export function useCourtKeys(onToggle: () => void, onJump: (d: -1 | 0 | 1) => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input,textarea")) return;
      if (e.code === "Space") {
        e.preventDefault();
        onToggle();
      }
      if (e.key === "ArrowLeft") onJump(-1);
      if (e.key === "ArrowRight") onJump(1);
      if (e.key === "r" || e.key === "R") onJump(0);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onToggle, onJump]);
}

/** A small control pill in the corner of the stage — not a video player. */
export function StageControls({ onToggle, onJump, onVolume }: {
  onToggle: () => void; onJump: (d: -1 | 0 | 1) => void; onVolume: (v: number) => void;
}) {
  const { status, volume, subtitles, set } = usePlayer();
  const playing = status === "playing";
  const can = status === "playing" || status === "paused";
  const btn = "grid h-8 w-8 place-items-center rounded-full text-ivory/80 transition-colors hover:bg-white/10 hover:text-ivory disabled:opacity-30";
  return (
    <div className="pointer-events-auto flex items-center gap-0.5 rounded-full border border-white/10 bg-ink/55 p-1 backdrop-blur-md">
      <button className={btn} onClick={() => onJump(0)} disabled={!can} aria-label="Replay line" title="Replay line (R)">
        <RotateCcw className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={onToggle}
        disabled={!can}
        aria-label={playing ? "Pause" : "Play"}
        title={playing ? "Pause (Space)" : "Play (Space)"}
        className="grid h-8 w-8 place-items-center rounded-full bg-ivory text-ink transition-transform hover:scale-105 disabled:opacity-40"
      >
        {playing ? <Pause className="h-3.5 w-3.5 fill-current" /> : <Play className="h-3.5 w-3.5 translate-x-px fill-current" />}
      </button>
      <button className={btn} onClick={() => onVolume(volume ? 0 : 0.9)} aria-label={volume ? "Mute" : "Unmute"} title={volume ? "Mute" : "Unmute"}>
        {volume ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
      </button>
      <button className={btn} onClick={() => set({ subtitles: !subtitles })} aria-label={subtitles ? "Hide captions" : "Show captions"} title="Captions">
        {subtitles ? <Captions className="h-3.5 w-3.5" /> : <CaptionsOff className="h-3.5 w-3.5" />}
      </button>
    </div>
  );
}

/** Cinematic lower-third captions inside the stage. Words light up as they're spoken. */
export function StageCaptions({ characters, hidden }: { characters: CharacterInfo[]; hidden?: boolean }) {
  const seg = usePlayer((s) => s.segment);
  const word = usePlayer((s) => s.wordIndex);
  const on = usePlayer((s) => s.subtitles);
  const speaker = characters.find((c) => c.key === seg?.speaker);
  const words = seg?.audio?.words.length ? seg.audio.words.map((w) => w.w) : seg?.subtitle.split(" ") ?? [];
  const emphasis = new Set((seg?.text.match(/\*([^*]+)\*/g) ?? []).flatMap((m) => m.slice(1, -1).toLowerCase().split(" ")));
  // Film-style subtitles: show only the current phrase (≈ one sentence, max ~13 words), not the whole speech.
  const chunks: [number, number][] = [];
  let start = 0;
  words.forEach((w, i) => {
    const end = /[.!?…]["”’]?$/.test(w) || i - start >= 12 || i === words.length - 1;
    if (end) {
      chunks.push([start, i]);
      start = i + 1;
    }
  });
  const active = Math.max(0, word);
  const [from, to] = chunks.find(([a, b]) => active >= a && active <= b) ?? chunks[0] ?? [0, -1];
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-[12]" aria-live="polite">
      <div className="bg-gradient-to-t from-black/80 via-black/30 to-transparent px-[5%] pb-[3%] pt-[6%]">
        <AnimatePresence mode="wait">
          {seg && on && !hidden && (
            <motion.div key={seg.turn_key} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.28 }}
              className="mx-auto max-w-[52rem] text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-gold/40 bg-black/50 px-3 py-1 font-mono text-[9px] uppercase tracking-[0.22em] sm:text-[10px]">
                <span className="text-gold">{speaker?.name ?? seg.speaker}</span>
                <span className="text-ivory/50">{speaker ? (speaker.surprise ? "Surprise witness" : ROLE_LABEL[speaker.role]) : ""}</span>
              </div>
              <p key={from} className="mt-2 font-display text-[clamp(0.95rem,1.65vw,1.5rem)] leading-snug [text-shadow:0_2px_12px_rgba(0,0,0,0.95)]">
                {words.slice(from, to + 1).map((w, k) => {
                  const i = from + k;
                  const clean = w.replace(/[^\p{L}\p{N}'’-]/gu, "").toLowerCase();
                  return (
                    <span key={i} className={cn("transition-colors duration-150", i <= word ? "text-ivory" : "text-ivory/35", emphasis.has(clean) && "italic text-gold")}>
                      {w}{" "}
                    </span>
                  );
                })}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/** A hairline of progress along the bottom edge of the stage. */
export function SceneProgress() {
  const position = usePlayer((s) => s.position);
  const duration = usePlayer((s) => s.duration);
  const pct = duration ? Math.min(100, (position / duration) * 100) : 0;
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-[13] h-[2px] bg-white/5">
      <div className="h-full bg-gold/80 transition-[width] duration-150 ease-linear" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function WaitingNote() {
  const status = usePlayer((s) => s.status);
  const text: Record<string, string> = {
    interrupted: "The court awaits the jury.",
    buffering: "The court is conferring…",
    paused: "Paused. The judge is pretending this was planned.",
  };
  if (!text[status]) return null;
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-[6%] z-[12] text-center font-display text-xl italic text-ivory/70 [text-shadow:0_2px_10px_rgba(0,0,0,0.9)]">
      {text[status]}
    </div>
  );
}
