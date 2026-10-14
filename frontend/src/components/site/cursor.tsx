"use client";

import { useEffect, useRef, useState } from "react";

/** A gold ring that trails the pointer; over anything clickable it becomes a little gavel. Desktop only. */
export function CourtCursor() {
  const ring = useRef<HTMLDivElement>(null);
  const dot = useRef<HTMLDivElement>(null);
  const [enabled, setEnabled] = useState(false);
  const [hot, setHot] = useState(false);
  const [down, setDown] = useState(false);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const id = setTimeout(() => setEnabled(fine), 0);
    if (!fine) return () => clearTimeout(id);
    let x = -100, y = -100, rx = -100, ry = -100, raf = 0;
    const move = (e: PointerEvent) => {
      x = e.clientX;
      y = e.clientY;
      if (dot.current) dot.current.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      const t = e.target as HTMLElement | null;
      setHot(!!t?.closest("a,button,[role=radio],[role=tab],input[type=range],summary,select"));
    };
    const tick = () => {
      rx += (x - rx) * 0.2;
      ry += (y - ry) * 0.2;
      if (ring.current) ring.current.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      raf = requestAnimationFrame(tick);
    };
    const d = () => setDown(true);
    const u = () => setDown(false);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerdown", d);
    window.addEventListener("pointerup", u);
    raf = requestAnimationFrame(tick);
    document.documentElement.classList.add("court-cursor");
    return () => {
      clearTimeout(id);
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", d);
      window.removeEventListener("pointerup", u);
      document.documentElement.classList.remove("court-cursor");
    };
  }, []);

  if (!enabled) return null;
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-[200]">
      <div ref={ring} className="absolute left-0 top-0">
        <div
          className="-translate-x-1/2 -translate-y-1/2 rounded-full border border-gold/70 transition-[width,height,background-color,opacity] duration-200"
          style={{ width: hot ? 46 : 28, height: hot ? 46 : 28, backgroundColor: hot ? "rgb(214 174 98 / 0.12)" : "transparent" }}
        />
      </div>
      <div ref={dot} className="absolute left-0 top-0">
        {hot ? (
          <svg viewBox="0 0 24 24" className="-translate-x-1/2 -translate-y-1/2 transition-transform duration-100" width="22" height="22"
            style={{ transform: `translate(-50%,-50%) rotate(${down ? -55 : -20}deg)` }}>
            <rect x="9" y="2" width="12" height="7" rx="1.5" fill="#d6ae62" />
            <rect x="13.2" y="8" width="3.6" height="13" rx="1.2" fill="#8f7444" />
          </svg>
        ) : (
          <div className="h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gold" />
        )}
      </div>
    </div>
  );
}
