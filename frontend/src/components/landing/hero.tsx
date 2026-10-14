"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { StageSwitch, useStageMode } from "@/components/court3d/stage-switch";
import { DEMO_CAST, DEMO_LINES } from "@/lib/demo-cast";
import type { Reaction } from "@/lib/types";
import { ROLE_LABEL } from "@/lib/utils";

/** Decorative mouth motion for the silent preview (no audio is playing here). */
const fakeAmplitude = () => {
  const t = performance.now() / 1000;
  return Math.max(0, Math.sin(t * 13) * 0.09 + Math.sin(t * 7.3) * 0.06 + 0.04);
};

export function Hero() {
  const [i, setI] = useState(0);
  const [talking, setTalking] = useState(true);
  useEffect(() => {
    const line = DEMO_LINES[i];
    const talkMs = 900 + line.text.length * 38;
    const a = setTimeout(() => setTalking(false), talkMs);
    const b = setTimeout(() => {
      setI((n) => (n + 1) % DEMO_LINES.length);
      setTalking(true);
    }, talkMs + 900);
    return () => {
      clearTimeout(a);
      clearTimeout(b);
    };
  }, [i]);
  const [stageMode] = useStageMode();
  const line = DEMO_LINES[i];
  const speaker = DEMO_CAST.find((c) => c.key === line.speaker)!;
  const reactions = useMemo<Record<string, Reaction>>(
    (): Record<string, Reaction> => {
      if (line.speaker === "defense") return { judge: "facepalm" };
      if (line.speaker === "witness_1") return { defendant: "gasp" };
      return {};
    },
    [line.speaker],
  );

  return (
    <section className="relative mx-auto w-full max-w-[1400px] px-4 pb-16 pt-6 sm:px-8 lg:pt-10">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[900px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgb(214_174_98/0.10),transparent)]" />
      <div className="grid items-center gap-10 lg:grid-cols-[0.92fr_1.08fr] lg:gap-14">
        <div className="relative">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="eyebrow flex items-center gap-3"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-burgundy-bright animate-blink" />
            The Court of Absolute Nonsense · Now in session
          </motion.div>
          <h1 className="mt-6 font-display text-[clamp(3.1rem,6.4vw,6.9rem)] leading-[0.88] text-balance">
            <motion.span className="block" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}>
              Order in the court.
            </motion.span>
            <motion.span
              className="block italic text-gold"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.9, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
            >
              Absolutely none in the arguments.
            </motion.span>
          </h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.8 }}
            className="mt-8 max-w-[34rem] text-lg leading-relaxed text-ivory-dim"
          >
            Your most ridiculous problems deserve a ridiculously serious trial. AI lawyers argue, witnesses crack,
            and a very tired judge delivers the verdict — fully voiced.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.55, duration: 0.6 }}
            className="mt-10 flex flex-wrap items-center gap-3"
          >
            <Link
              href="/file"
              className="group inline-flex items-center gap-3 rounded-full bg-gold px-7 py-4 text-[15px] font-semibold text-ink shadow-[0_10px_40px_-10px_rgb(214_174_98/0.6)] transition-transform hover:-translate-y-0.5"
            >
              Put something on trial
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
            <Link
              href="/case/the-people-vs-javascript"
              className="inline-flex items-center gap-3 rounded-full border border-line-strong px-6 py-4 text-[15px] text-ivory transition-colors hover:border-ivory/40 hover:bg-white/[0.03]"
            >
              <span className="grid h-6 w-6 place-items-center rounded-full bg-ivory text-ink">
                <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 translate-x-px fill-current"><path d="M2 1 L9 5 L2 9Z" /></svg>
              </span>
              Watch a ridiculous case
            </Link>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
          className="relative"
        >
          <StageSwitch
            mode={stageMode}
            burst={line.speaker === "defense" && talking ? i : 0}
            characters={DEMO_CAST}
            speaker={talking ? line.speaker : null}
            emotion={line.emotion}
            reactions={talking ? reactions : {}}
            amplitude={fakeAmplitude}
            witnessKey="witness_1"
            caseNumber="CR-2026-0001"
            caseTitle="The People vs. JavaScript"
            className="shadow-[0_40px_120px_-40px_rgba(0,0,0,0.9)]"
          />
          <div className="relative -mt-px rounded-b-[18px] border-x border-b hairline bg-ink-2/80 px-5 py-4 backdrop-blur sm:px-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.35 }}
                className="min-h-[4.5rem]"
              >
                <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em]">
                  <span className="text-gold">{speaker.name}</span>
                  <span className="text-mute">· {ROLE_LABEL[speaker.role]}</span>
                </div>
                <p className="mt-1.5 font-display text-[1.35rem] leading-snug text-ivory sm:text-2xl">“{line.text}”</p>
              </motion.div>
            </AnimatePresence>
          </div>
          <div className="mt-3 text-right font-mono text-[10px] tracking-[0.18em] text-mute">
            SILENT PREVIEW · FROM THE PEOPLE VS. JAVASCRIPT
          </div>
        </motion.div>
      </div>
    </section>
  );
}
