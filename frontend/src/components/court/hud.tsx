"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { usePlayer } from "@/stores/player";

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
