"use client";

import { AnimatePresence, motion } from "motion/react";
import { Pause, Play, Rewind, SkipBack, SkipForward, Subtitles, Volume2, VolumeX } from "lucide-react";
import { useEffect, useState } from "react";
import type { CharacterInfo } from "@/lib/types";
import { cn, formatMs, ROLE_LABEL } from "@/lib/utils";
import { usePlayer } from "@/stores/player";

/** Live subtitles: words light up as they are spoken; *emphasis* renders italic. */
export function DialogueSubtitle({ characters }: { characters: CharacterInfo[] }) {
  const seg = usePlayer((s) => s.segment);
  const word = usePlayer((s) => s.wordIndex);
  const on = usePlayer((s) => s.subtitles);
  const speaker = characters.find((c) => c.key === seg?.speaker);
  const words = seg?.audio?.words.length ? seg.audio.words.map((w) => w.w) : seg?.subtitle.split(" ") ?? [];
  const emphasis = new Set((seg?.text.match(/\*([^*]+)\*/g) ?? []).flatMap((m) => m.slice(1, -1).toLowerCase().split(" ")));
  return (
    <div className="relative min-h-[8.5rem] px-5 py-4 sm:px-7" aria-live="polite">
      <AnimatePresence mode="wait">
        {seg && on && (
          <motion.div key={seg.turn_key} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.25 }}>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[10px] uppercase tracking-[0.2em]">
              <span className="text-gold">{speaker?.name ?? seg.speaker}</span>
              <span className="text-mute">· {speaker ? (speaker.surprise ? "Surprise witness" : ROLE_LABEL[speaker.role]) : ""}</span>
              {seg.delivery && <span className="normal-case tracking-normal text-mute/80 italic">({seg.delivery})</span>}
            </div>
            <p className="mt-2 font-display text-[1.3rem] leading-snug sm:text-[1.6rem]">
              {words.map((w, i) => {
                const clean = w.replace(/[^\p{L}\p{N}'’-]/gu, "").toLowerCase();
                return (
                  <span
                    key={i}
                    className={cn(
                      "transition-colors duration-150",
                      i <= word ? "text-ivory" : "text-ivory/25",
                      emphasis.has(clean) && "italic text-gold",
                    )}
                  >
                    {w}{" "}
                  </span>
                );
              })}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
      {!seg && on && <WaitingLine />}
    </div>
  );
}

function WaitingLine() {
  const status = usePlayer((s) => s.status);
  const text: Record<string, string> = {
    interrupted: "The court awaits the jury.",
    buffering: "The court is conferring…",
    paused: "Paused. The judge is pretending this was planned.",
    completed: "Court is adjourned.",
  };
  return <p className="pt-6 font-display text-2xl italic text-mute">{text[status] ?? ""}</p>;
}

/** AudioTimeline: per-scene scrubber with line ticks, plus transport controls. */
export function AudioTimeline({ onToggle, onSeek, onJump, onVolume }: {
  onToggle: () => void; onSeek: (s: number) => void; onJump: (d: -1 | 0 | 1) => void; onVolume: (v: number) => void;
}) {
  const { status, position, duration, volume, subtitles, sceneTitle, queueKind, set } = usePlayer();
  const playing = status === "playing";
  const can = status === "playing" || status === "paused";
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input,textarea")) return;
      if (e.code === "Space") { e.preventDefault(); onToggle(); }
      if (e.key === "ArrowLeft") onJump(-1);
      if (e.key === "ArrowRight") onJump(1);
      if (e.key === "r") onJump(0);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onToggle, onJump]);
  return (
    <div className="flex items-center gap-3 border-t hairline px-4 py-3 sm:gap-4 sm:px-6">
      <div className="flex items-center gap-1">
        <IconBtn label="Previous line" onClick={() => onJump(-1)} disabled={!can}><SkipBack className="h-4 w-4" /></IconBtn>
        <button
          onClick={onToggle}
          disabled={!can}
          aria-label={playing ? "Pause" : "Play"}
          className="grid h-10 w-10 place-items-center rounded-full bg-ivory text-ink transition-transform hover:scale-105 disabled:opacity-40"
        >
          {playing ? <Pause className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 translate-x-px fill-current" />}
        </button>
        <IconBtn label="Next line" onClick={() => onJump(1)} disabled={!can}><SkipForward className="h-4 w-4" /></IconBtn>
        <IconBtn label="Replay line" onClick={() => onJump(0)} disabled={!can}><Rewind className="h-4 w-4" /></IconBtn>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex justify-between font-mono text-[10px] uppercase tracking-[0.16em] text-mute">
          <span className="truncate">{queueKind === "response" ? "Responding to the jury" : sceneTitle}</span>
          <span>{formatMs(position * 1000)} / {formatMs(duration * 1000)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={Math.max(duration, 0.1)}
          step={0.1}
          value={Math.min(position, duration)}
          disabled={!can}
          onChange={(e) => onSeek(Number(e.target.value))}
          aria-label="Seek within scene"
          className="drama-range mt-2 w-full"
          style={{ "--fill": `${duration ? (position / duration) * 100 : 0}%` } as React.CSSProperties}
        />
      </div>
      <IconBtn label={subtitles ? "Hide subtitles" : "Show subtitles"} onClick={() => set({ subtitles: !subtitles })} active={subtitles}>
        <Subtitles className="h-4 w-4" />
      </IconBtn>
      <div className="hidden items-center gap-2 sm:flex">
        <IconBtn label={volume ? "Mute" : "Unmute"} onClick={() => onVolume(volume ? 0 : 0.9)}>
          {volume ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
        </IconBtn>
        <input type="range" min={0} max={1} step={0.05} value={volume} onChange={(e) => onVolume(Number(e.target.value))}
          aria-label="Volume" className="drama-range w-20" style={{ "--fill": `${volume * 100}%` } as React.CSSProperties} />
      </div>
    </div>
  );
}

function IconBtn({ children, label, onClick, disabled, active }: {
  children: React.ReactNode; label: string; onClick: () => void; disabled?: boolean; active?: boolean;
}) {
  return (
    <button onClick={onClick} disabled={disabled} aria-label={label} title={label}
      className={cn("grid h-9 w-9 place-items-center rounded-full text-mute transition-colors hover:bg-white/5 hover:text-ivory disabled:opacity-30",
        active && "text-gold")}>
      {children}
    </button>
  );
}

/** The Ace-Attorney-style burst. Short, loud, then gone. */
export function ObjectionBurst() {
  const burst = usePlayer((s) => s.burst);
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!burst) return;
    const on = setTimeout(() => setShow(true), 0);
    const off = setTimeout(() => setShow(false), 950);
    return () => {
      clearTimeout(on);
      clearTimeout(off);
    };
  }, [burst]);
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key={burst}
          className="pointer-events-none absolute inset-0 z-30 grid place-items-center overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12 }}
        >
          <motion.div className="absolute inset-x-[-10%] h-[34%] -rotate-6 bg-burgundy" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.18, ease: [0.7, 0, 0.84, 0] }} />
          <motion.span
            className="relative font-display text-[clamp(3rem,11vw,9rem)] italic leading-none text-ivory [text-shadow:0_6px_0_#090909]"
            initial={{ scale: 2.2, rotate: -8, opacity: 0 }}
            animate={{ scale: 1, rotate: -6, opacity: 1 }}
            transition={{ type: "spring", stiffness: 520, damping: 16 }}
          >
            Objection!
          </motion.span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function SceneTitleCard() {
  const card = usePlayer((s) => s.titleCard);
  return (
    <AnimatePresence>
      {card && (
        <motion.div
          className="absolute inset-0 z-20 grid place-items-center bg-ink/80 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}
        >
          <div className="text-center">
            <motion.div className="eyebrow text-gold" initial={{ y: 8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}>{card.phase}</motion.div>
            <motion.h2 className="mt-3 font-display text-[clamp(2.4rem,6vw,5rem)] italic leading-none" initial={{ y: 14, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.18, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>
              {card.title}
            </motion.h2>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Exhibit floats onto the stage while it is being presented. */
export function StageExhibit({ evidence }: { evidence: { id: string; title: string; description: string }[] }) {
  const id = usePlayer((s) => s.evidenceId);
  const e = evidence.find((x) => x.id === id);
  return (
    <AnimatePresence>
      {e && (
        <motion.div
          key={e.id}
          className="absolute left-1/2 top-[10%] z-20 w-[min(46%,420px)] -translate-x-1/2"
          initial={{ opacity: 0, y: 40, rotate: -4 }}
          animate={{ opacity: 1, y: 0, rotate: -2 }}
          exit={{ opacity: 0, y: -20, rotate: 2 }}
          transition={{ type: "spring", stiffness: 200, damping: 22 }}
        >
          <div className="rounded-xl border border-gold/60 bg-[#efe7d6] p-4 text-ink shadow-[0_30px_60px_-20px_rgba(0,0,0,0.9)] sm:p-5">
            <div className="flex justify-between font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-burgundy">
              <span>Exhibit {e.id}</span><span>Fictional</span>
            </div>
            <div className="mt-2 font-display text-2xl leading-tight sm:text-3xl">{e.title}</div>
            <p className="mt-1.5 hidden text-sm leading-snug text-ink/75 sm:block">{e.description}</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
