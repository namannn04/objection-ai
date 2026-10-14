"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { eventsUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

const MESSAGES = [
  "Finding lawyers willing to defend this nonsense.",
  "Reviewing evidence that probably should not exist.",
  "The judge is questioning their career choices.",
  "Subpoenaing a witness who would rather not.",
  "Polishing the gavel. Aggressively.",
  "Teaching the defendant to say ‘no comment’.",
  "Rehearsing dramatic pauses. Pausing. Still pausing.",
];

interface FeedLine { speaker: string; text: string; source: string }

export interface PrepProgress {
  title?: string;
  sceneIndex?: number;
  sceneTotal?: number;
  sceneTitle?: string;
  audioDone?: number;
  audioTotal?: number;
  humor: number[];
  lines: FeedLine[];
  stage: string;
}

/** Subscribes to the case's live preparation events (SSE). */
export function usePrepEvents(ref: string, enabled: boolean) {
  const [p, setP] = useState<PrepProgress>({ humor: [], lines: [], stage: "" });
  useEffect(() => {
    if (!enabled) return;
    const es = new EventSource(eventsUrl(ref));
    const on = (name: string, fn: (d: Record<string, unknown>) => void) =>
      es.addEventListener(name, (e) => fn(JSON.parse((e as MessageEvent).data || "{}")));
    on("planned", (d) => setP((x) => ({ ...x, title: d.title as string, stage: "planned" })));
    on("strategizing", () => setP((x) => ({ ...x, stage: "strategizing" })));
    on("scene", (d) => setP((x) => ({ ...x, stage: "scene", sceneIndex: d.index as number, sceneTotal: d.total as number, sceneTitle: d.title as string })));
    on("line", (d) => setP((x) => ({ ...x, lines: [...x.lines, { speaker: d.speaker as string, text: d.text as string, source: d.source as string }].slice(-40) })));
    on("scene_done", (d) => setP((x) => ({ ...x, humor: [...x.humor, d.humor as number] })));
    on("windows", () => setP((x) => ({ ...x, stage: "windows" })));
    on("validated", () => setP((x) => ({ ...x, stage: "validated" })));
    on("audio", (d) => setP((x) => ({ ...x, stage: "audio", audioDone: d.done as number, audioTotal: d.total as number })));
    return () => es.close();
  }, [ref, enabled]);
  return p;
}

const STEPS = [
  { key: "CASE_CREATED", label: "Case filed" },
  { key: "SCRIPT_PLANNING", label: "Casting & writing the trial" },
  { key: "SCRIPT_VALIDATION", label: "Checking the record" },
  { key: "AUDIO_PREPARATION", label: "Recording the voices" },
  { key: "COURTROOM_READY", label: "Courtroom ready" },
];
const ORDER = ["CASE_CREATED", "CASE_PREPARATION", "SCRIPT_PLANNING", "SCRIPT_VALIDATION", "AUDIO_PREPARATION", "COURTROOM_READY"];

export function CaseProgressIndicator({ status }: { status: string }) {
  const at = ORDER.indexOf(status);
  return (
    <ol className="grid gap-3">
      {STEPS.map((s) => {
        const idx = ORDER.indexOf(s.key);
        const done = at > idx || status === "COURTROOM_READY";
        const current = !done && (at === idx || (s.key === "SCRIPT_PLANNING" && status === "CASE_PREPARATION"));
        return (
          <li key={s.key} className="flex items-center gap-3">
            <span className={cn("grid h-5 w-5 place-items-center rounded-full border text-[10px]",
              done ? "border-gold bg-gold text-ink" : current ? "border-gold text-gold" : "border-line-strong text-mute")}>
              {done ? "✓" : current ? <span className="h-1.5 w-1.5 animate-ping rounded-full bg-gold" /> : ""}
            </span>
            <span className={cn("text-sm", done ? "text-ivory" : current ? "text-gold" : "text-mute")}>{s.label}</span>
          </li>
        );
      })}
    </ol>
  );
}

export function GenerationProgress({ status, caseNumber, defendant, progress, running }: {
  status: string; caseNumber: string; defendant: string; progress: PrepProgress; running: boolean;
}) {
  const [m, setM] = useState(0);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setM((x) => (x + 1) % MESSAGES.length), 3200);
    return () => clearInterval(t);
  }, [running]);
  const feed = useRef<HTMLDivElement>(null);
  useEffect(() => {
    feed.current?.scrollTo({ top: feed.current.scrollHeight, behavior: "smooth" });
  }, [progress.lines.length]);

  const pct =
    status === "AUDIO_PREPARATION" && progress.audioTotal
      ? 70 + 30 * ((progress.audioDone ?? 0) / progress.audioTotal)
      : progress.sceneTotal
        ? 10 + 60 * ((progress.sceneIndex ?? 0) / progress.sceneTotal)
        : status === "CASE_CREATED" ? 3 : 8;

  return (
    <div className="mx-auto grid w-full max-w-[1300px] gap-10 lg:grid-cols-[1fr_1.1fr]">
      <div>
        <div className="font-mono text-[11px] tracking-[0.2em] text-mute">{caseNumber} · IN PREPARATION</div>
        <h1 className="mt-5 font-display text-[clamp(2.8rem,6vw,5.4rem)] leading-[0.92] text-balance">
          {progress.title ?? <>The People vs. <span className="italic text-gold">{defendant}</span></>}
        </h1>
        <div className="mt-10 h-px w-full bg-ink-4">
          <motion.div className="h-px bg-gold" animate={{ width: `${pct}%` }} transition={{ duration: 0.8 }} />
        </div>
        <div className="mt-6 min-h-[2rem]">
          <AnimatePresence mode="wait">
            {running && (
              <motion.p key={m} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                className="font-display text-2xl italic text-ivory-dim">
                {MESSAGES[m]}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
        <div className="mt-10">
          <CaseProgressIndicator status={status} />
        </div>
        {progress.sceneTitle && status === "SCRIPT_PLANNING" && (
          <p className="mt-6 font-mono text-[11px] uppercase tracking-[0.18em] text-mute">
            Writing scene {(progress.sceneIndex ?? 0) + 1} of {progress.sceneTotal}: <span className="text-ivory">{progress.sceneTitle}</span>
          </p>
        )}
        {status === "AUDIO_PREPARATION" && progress.audioTotal && (
          <p className="mt-6 font-mono text-[11px] uppercase tracking-[0.18em] text-mute">
            Recorded {progress.audioDone} of {progress.audioTotal} lines
          </p>
        )}
      </div>

      <div className="rounded-2xl border hairline bg-ink-2">
        <div className="flex items-center justify-between border-b hairline px-5 py-3">
          <span className="eyebrow">Rehearsal room · live</span>
          <span className="font-mono text-[10px] text-mute">{progress.lines.length} lines written</span>
        </div>
        <div ref={feed} className="h-[440px] overflow-y-auto px-5 py-4">
          {progress.lines.length === 0 && (
            <p className="pt-24 text-center text-sm text-mute">The agents are reading the case file. Lines appear here as each character writes them.</p>
          )}
          <AnimatePresence initial={false}>
            {progress.lines.map((l, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="mb-4">
                <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em]">
                  <span className="text-gold">{l.speaker}</span>
                  {l.source === "fallback" && <span className="rounded border border-line-strong px-1 text-mute">scripted fallback</span>}
                </div>
                <p className="mt-1 text-[15px] leading-relaxed text-ivory-dim">{l.text}</p>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
