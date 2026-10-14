"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";

/** First visit per session: the curtains part on a gavel strike. Skips itself after that. */
export function CourtIntro() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    let seen = false;
    try {
      seen = sessionStorage.getItem("objection.intro") === "1";
      sessionStorage.setItem("objection.intro", "1");
    } catch {
      seen = true;
    }
    if (seen || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const on = setTimeout(() => setShow(true), 0);
    const off = setTimeout(() => setShow(false), 1650);
    return () => {
      clearTimeout(on);
      clearTimeout(off);
    };
  }, []);
  return (
    <AnimatePresence>
      {show && (
        <motion.div className="fixed inset-0 z-[150] grid place-items-center" exit={{ opacity: 1 }} transition={{ duration: 0.9 }}>
          <motion.div className="absolute inset-y-0 left-0 w-1/2 bg-burgundy" exit={{ x: "-100%" }} transition={{ duration: 0.85, ease: [0.7, 0, 0.2, 1] }}
            style={{ backgroundImage: "repeating-linear-gradient(90deg, rgba(0,0,0,0.25) 0 2px, transparent 2px 36px)" }} />
          <motion.div className="absolute inset-y-0 right-0 w-1/2 bg-burgundy" exit={{ x: "100%" }} transition={{ duration: 0.85, ease: [0.7, 0, 0.2, 1] }}
            style={{ backgroundImage: "repeating-linear-gradient(90deg, rgba(0,0,0,0.25) 0 2px, transparent 2px 36px)" }} />
          <motion.div
            className="relative text-center"
            initial={{ scale: 1.6, opacity: 0 }}
            animate={{ scale: [1.6, 0.94, 1], opacity: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.45, times: [0, 0.7, 1], ease: [0.7, 0, 0.84, 0] }}
          >
            <div className="font-display text-[clamp(4rem,14vw,12rem)] italic leading-none text-ivory [text-shadow:0_8px_0_#2a0d12]">Order!</div>
            <div className="mt-3 font-mono text-[11px] tracking-[0.4em] text-gold">THE COURT OF ABSOLUTE NONSENSE</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
