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

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 40 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 1, delay, ease: [0.22, 1, 0.36, 1] as const },
});

/** Full-bleed movie-poster hero: the live 3D courtroom is the backdrop. */
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
  const reactions = useMemo((): Record<string, Reaction> => {
    if (line.speaker === "defense") return { judge: "facepalm" };
    if (line.speaker === "witness_1") return { defendant: "gasp" };
    return {};
  }, [line.speaker]);

  return (
    <section className="relative isolate h-[100svh] min-h-[680px] w-full overflow-hidden bg-black">
      {/* the live courtroom, full bleed */}
      <motion.div className="absolute inset-0 -z-10" initial={{ scale: 1.08, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 2.2, ease: [0.22, 1, 0.36, 1] }}>
        <StageSwitch
          mode={stageMode}
          minimal
          burst={line.speaker === "defense" && talking ? i : 0}
          characters={DEMO_CAST}
          speaker={talking ? line.speaker : null}
          emotion={line.emotion}
          reactions={talking ? reactions : {}}
          amplitude={fakeAmplitude}
          witnessKey="witness_1"
          className="absolute inset-0 aspect-auto h-full rounded-none border-0"
        />
      </motion.div>
      {/* legibility: a dark wash from the left and the bottom */}
      <div className="pointer-events-none absolute inset-0 -z-[5] bg-[linear-gradient(90deg,rgba(5,4,4,0.92)_0%,rgba(5,4,4,0.72)_34%,rgba(5,4,4,0.15)_62%,transparent_80%)]" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 -z-[5] h-[45%] bg-gradient-to-t from-ink via-ink/70 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-[5] h-40 bg-gradient-to-b from-black/80 to-transparent" />

      <div className="mx-auto flex h-full w-full max-w-[1500px] flex-col justify-end px-5 pb-[7vh] pt-28 sm:px-10">
        <div className="grid items-end gap-10 lg:grid-cols-[1fr_380px]">
          <div>
            <motion.div {...rise(0.15)} className="flex flex-wrap items-center gap-3 font-mono text-[11px] uppercase tracking-[0.24em] text-ivory/70">
              <span className="flex items-center gap-2 rounded-full border border-burgundy-bright/50 bg-burgundy/30 px-3 py-1 text-ivory">
                <span className="h-1.5 w-1.5 animate-blink rounded-full bg-[#ff4a5c]" /> Now in session
              </span>
              <span>The Court of Absolute Nonsense</span>
            </motion.div>

            <h1 className="mt-6 font-poster leading-[0.84] text-ivory">
              <motion.span {...rise(0.3)} className="block text-[clamp(4.2rem,13.5vw,13.5rem)]">Order in</motion.span>
              <motion.span {...rise(0.42)} className="block text-[clamp(4.2rem,13.5vw,13.5rem)]">
                the court<span className="text-gold">.</span>
              </motion.span>
            </h1>
            <motion.p {...rise(0.6)} className="mt-4 font-display text-[clamp(1.6rem,3.6vw,3.4rem)] italic leading-[1.05] text-gold [font-variation-settings:'SOFT'_100,'WONK'_1,'opsz'_144]">
              Absolutely none in the arguments.
            </motion.p>
            <motion.p {...rise(0.75)} className="mt-6 max-w-[34rem] text-[17px] leading-relaxed text-ivory/75">
              Put anything on trial — your Wi-Fi, Monday, JavaScript. AI lawyers argue it with a straight face, witnesses crack,
              and a deeply tired judge delivers the verdict. Fully voiced.
            </motion.p>
            <motion.div {...rise(0.9)} className="mt-9 flex flex-wrap items-center gap-3">
              <Link href="/file"
                className="group inline-flex items-center gap-3 rounded-full bg-gold px-8 py-4 text-[15px] font-semibold uppercase tracking-[0.08em] text-ink shadow-[0_14px_50px_-12px_rgb(214_174_98/0.75)] transition-transform hover:-translate-y-0.5">
                Put something on trial
                <span className="transition-transform group-hover:translate-x-1">→</span>
              </Link>
              <Link href="/case/the-people-vs-javascript"
                className="inline-flex items-center gap-3 rounded-full border border-ivory/25 bg-black/30 px-6 py-4 text-[15px] text-ivory backdrop-blur-sm transition-colors hover:border-ivory/50 hover:bg-white/5">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-ivory text-ink">
                  <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 translate-x-px fill-current"><path d="M2 1 L9 5 L2 9Z" /></svg>
                </span>
                Watch a ridiculous case
              </Link>
            </motion.div>
          </div>

          {/* live transcript card */}
          <motion.div {...rise(1.05)} className="hidden lg:block">
            <div className="rounded-2xl border border-white/10 bg-black/45 p-5 backdrop-blur-md">
              <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.2em] text-ivory/50">
                <span>Live from CR-2026-0001</span>
                <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 animate-blink rounded-full bg-[#ff4a5c]" />Rec</span>
              </div>
              <AnimatePresence mode="wait">
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.35 }}
                  className="mt-4 min-h-[7.5rem]">
                  <div className="font-mono text-[10px] uppercase tracking-[0.2em]">
                    <span className="text-gold">{speaker.name}</span> <span className="text-ivory/40">· {ROLE_LABEL[speaker.role]}</span>
                  </div>
                  <p className="mt-2 font-display text-[1.45rem] italic leading-snug text-ivory">“{line.text}”</p>
                </motion.div>
              </AnimatePresence>
              <div className="mt-3 flex gap-1">
                {DEMO_LINES.map((_, k) => (
                  <span key={k} className={`h-[2px] flex-1 rounded-full transition-colors duration-500 ${k === i ? "bg-gold" : k < i ? "bg-ivory/40" : "bg-ivory/10"}`} />
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* scroll cue */}
      <motion.div {...rise(1.4)} className="pointer-events-none absolute bottom-5 left-1/2 hidden -translate-x-1/2 flex-col items-center gap-2 font-mono text-[9px] uppercase tracking-[0.3em] text-ivory/40 sm:flex">
        Scroll for the docket
        <span className="h-8 w-px animate-pulse bg-gradient-to-b from-gold to-transparent" />
      </motion.div>
    </section>
  );
}
