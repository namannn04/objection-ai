"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { CharacterPortrait } from "@/components/characters/character-portrait";
import type { AmplitudeSource } from "@/components/characters/face-parts";
import type { CharacterInfo, Reaction } from "@/lib/types";
import { benchPlate, cn } from "@/lib/utils";

type Seat = "judge" | "prosecutor" | "defense" | "defendant" | "witness" | "reporter";

// Seat geometry in % of the stage box: x/y is the portrait's bottom-centre.
const SEATS: Record<Seat, { x: number; y: number; w: number; z: number }> = {
  judge: { x: 50, y: 44, w: 17.5, z: 2 },
  witness: { x: 77, y: 60, w: 14, z: 3 },
  defendant: { x: 50, y: 88, w: 17, z: 5 },
  prosecutor: { x: 15.5, y: 101, w: 23, z: 6 },
  defense: { x: 84.5, y: 101, w: 23, z: 6 },
  reporter: { x: 8, y: 26, w: 8.5, z: 7 },
};

function seatOf(c: CharacterInfo, witnessKey?: string | null): Seat | null {
  if (c.role === "witness") return c.key === witnessKey ? "witness" : null;
  return c.role as Seat;
}

export interface StageProps {
  characters: CharacterInfo[];
  speaker?: string | null;
  emotion?: string;
  reactions?: Record<string, Reaction>;
  amplitude?: AmplitudeSource | null;
  witnessKey?: string | null;
  caseTitle?: string;
  caseNumber?: string;
  className?: string;
  children?: React.ReactNode;
  live?: boolean;
}

export function CourtroomStage({
  characters, speaker, emotion, reactions = {}, amplitude = null, witnessKey, caseNumber, className, children, live = true,
}: StageProps) {
  const reduce = useReducedMotion();
  const placed = characters
    .map((c) => ({ c, seat: seatOf(c, witnessKey ?? characters.find((x) => x.role === "witness" && !x.surprise)?.key) }))
    .filter((p): p is { c: CharacterInfo; seat: Seat } => p.seat !== null);
  const active = placed.find((p) => p.c.key === speaker);
  const focus = active ? SEATS[active.seat] : null;
  const cam = focus && !reduce && active?.seat !== "reporter"
    ? { x: (50 - focus.x) * 0.06, y: (60 - focus.y) * 0.05, s: 1.035 }
    : { x: 0, y: 0, s: 1 };

  return (
    <div className={cn("relative aspect-[16/9] w-full overflow-hidden rounded-[18px] bg-ink-2 hairline border", className)}>
      <motion.div
        className="absolute inset-0"
        animate={{ x: `${cam.x}%`, y: `${cam.y}%`, scale: cam.s }}
        transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
      >
        <Backdrop />

        {/* Spotlight on the active speaker */}
        <motion.div
          aria-hidden
          className="pointer-events-none absolute z-[1] h-[120%] w-[34%] -translate-x-1/2"
          style={{ top: "-14%", background: "radial-gradient(ellipse 50% 70% at 50% 72%, rgb(255 236 196 / 0.20), transparent 70%)" }}
          animate={{ left: `${focus?.x ?? 50}%`, opacity: focus ? 1 : 0.35 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        />

        {/* Furniture behind the people */}
        <Bench name={benchPlate(characters.find((c) => c.role === "judge")?.name)} />
        <WitnessBox />

        {placed.map(({ c, seat }, i) => {
          const s = SEATS[seat];
          const isSpeaking = speaker === c.key;
          const portrait = (
            <CharacterPortrait
              character={c}
              speaking={isSpeaking}
              emotion={isSpeaking ? emotion : undefined}
              reaction={reactions[c.key] ?? null}
              amplitude={isSpeaking ? amplitude : null}
              dimmed={!!speaker && !isSpeaking}
              blinkDelay={i * 0.7}
              className="h-full w-full"
            />
          );
          if (seat === "reporter") {
            return (
              <div key={c.key} className="absolute z-[7]" style={{ left: `${s.x}%`, top: "5%", width: `${s.w}%`, transform: "translateX(-50%)" }}>
                <div className={cn("aspect-square overflow-hidden rounded-full border bg-ink-3 transition-colors duration-500",
                  isSpeaking ? "border-gold" : "border-line-strong")}>
                  <div className="h-[118%] w-full translate-y-[2%]">{portrait}</div>
                </div>
                <div className="mt-1.5 flex items-center justify-center gap-1 whitespace-nowrap font-mono text-[7px] tracking-[0.2em] text-mute sm:text-[9px]">
                  <span className={cn("h-1.5 w-1.5 rounded-full", live ? "bg-burgundy-bright animate-blink" : "bg-mute")} />ON AIR
                </div>
              </div>
            );
          }
          return (
            <AnimatePresence key={c.key}>
              <motion.div
                className="absolute"
                style={{ left: `${s.x}%`, top: `${s.y}%`, width: `${s.w}%`, zIndex: s.z, translateX: "-50%", translateY: "-100%" }}
                initial={seat === "witness" ? { opacity: 0, y: 12 } : false}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                transition={{ duration: 0.6 }}
              >
                <div className="aspect-[200/220] w-full">{portrait}</div>
              </motion.div>
            </AnimatePresence>
          );
        })}

        {/* Furniture in front of the people */}
        <Podium />
        <CounselTable side="left" label="The People" />
        <CounselTable side="right" label="The Defense" />
        <div className="pointer-events-none absolute inset-0 z-[8] bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(0,0,0,0.55))]" />
      </motion.div>

      {caseNumber && (
        <div className="absolute right-[2.5%] top-[4%] z-[9] text-right font-mono text-[9px] tracking-[0.2em] text-mute sm:text-[10px]">
          {caseNumber}
        </div>
      )}
      <div className="absolute inset-0 z-[10]">{children}</div>
    </div>
  );
}

function Backdrop() {
  return (
    <div aria-hidden className="absolute inset-0">
      {/* back wall panels */}
      <div className="absolute inset-0 bg-[linear-gradient(180deg,#1b1714_0%,#121110_55%,#0b0b0b_100%)]" />
      <div className="absolute inset-x-0 top-0 h-[62%] opacity-[0.35] bg-[repeating-linear-gradient(90deg,transparent_0,transparent_calc(8.33%-1px),rgb(214_174_98/0.18)_calc(8.33%-1px),rgb(214_174_98/0.18)_8.33%)]" />
      {/* light shafts from high windows */}
      <div className="absolute -top-[10%] left-[8%] h-[90%] w-[16%] rotate-[18deg] bg-[linear-gradient(180deg,rgb(255_230_180/0.10),transparent_80%)] blur-md" />
      <div className="absolute -top-[10%] right-[8%] h-[90%] w-[16%] -rotate-[18deg] bg-[linear-gradient(180deg,rgb(255_230_180/0.08),transparent_80%)] blur-md" />
      {/* the court seal */}
      <svg viewBox="0 0 200 200" className="absolute left-1/2 top-[3%] w-[21%] -translate-x-1/2 opacity-80">
        <defs>
          <path id="seal-arc" d="M100 100 m-74 0 a74 74 0 1 1 148 0 a74 74 0 1 1 -148 0" />
        </defs>
        <circle cx="100" cy="100" r="92" fill="none" stroke="#d6ae62" strokeOpacity="0.55" strokeWidth="1.2" />
        <circle cx="100" cy="100" r="62" fill="none" stroke="#d6ae62" strokeOpacity="0.35" strokeWidth="0.8" />
        <text fill="#d6ae62" fillOpacity="0.6" fontSize="10.5" letterSpacing="3.2" fontFamily="var(--font-geist-mono)">
          <textPath href="#seal-arc">THE COURT OF ABSOLUTE NONSENSE · EST. 2026 · ORDER ·</textPath>
        </text>
        {/* scales of justice, slightly unbalanced */}
        <g stroke="#d6ae62" strokeOpacity="0.7" strokeWidth="2" fill="none" strokeLinecap="round">
          <path d="M100 66 L100 132 M84 136 L116 136" />
          <path d="M70 80 L130 74" />
          <path d="M70 80 L60 104 M70 80 L80 104 M130 74 L120 98 M130 74 L140 98" strokeWidth="1.2" />
          <path d="M58 104 Q70 114 82 104 M118 98 Q130 108 142 98" />
        </g>
      </svg>
      {/* floor */}
      <div className="absolute inset-x-0 bottom-0 h-[42%] bg-[linear-gradient(180deg,#14100d,#0a0908)]" />
      <div className="absolute inset-x-0 bottom-0 h-[42%] opacity-30 [background:repeating-linear-gradient(90deg,transparent_0_6%,rgb(214_174_98/0.08)_6%_6.2%)] [transform:perspective(400px)_rotateX(55deg)] origin-bottom" />
    </div>
  );
}

function Bench({ name }: { name: string }) {
  return (
    <div className="absolute left-1/2 top-[40%] z-[3] h-[17%] w-[36%] -translate-x-1/2">
      <div className="absolute inset-0 rounded-t-md bg-[linear-gradient(180deg,#2a211b,#17120f)] shadow-[0_20px_40px_rgba(0,0,0,0.6)]" />
      <div className="absolute inset-x-0 top-0 h-[10%] rounded-t-md bg-gold/70" />
      <div className="absolute left-1/2 top-[38%] -translate-x-1/2 rounded-sm border border-gold/40 bg-ink/70 px-[4%] py-[1.5%] font-mono text-[clamp(5px,0.75vw,10px)] tracking-[0.25em] text-gold/80 whitespace-nowrap">
        {name.toUpperCase()}
      </div>
    </div>
  );
}

function WitnessBox() {
  return (
    <div className="absolute left-[77%] top-[56%] z-[4] h-[13%] w-[18%] -translate-x-1/2">
      <div className="absolute inset-0 rounded-t-md bg-[linear-gradient(180deg,#261e19,#15110e)]" />
      <div className="absolute inset-x-0 top-0 h-[9%] rounded-t-md bg-gold/50" />
      <div className="absolute inset-x-0 top-[40%] text-center font-mono text-[clamp(5px,0.65vw,9px)] tracking-[0.3em] text-gold/60">WITNESS</div>
    </div>
  );
}

function Podium() {
  return (
    <div className="absolute left-1/2 top-[80%] z-[5] h-[16%] w-[17%] -translate-x-1/2">
      <div className="absolute inset-0 [clip-path:polygon(8%_0,92%_0,100%_100%,0_100%)] bg-[linear-gradient(180deg,#2c231d,#120e0b)]" />
      <div className="absolute inset-x-[8%] top-0 h-[8%] bg-gold/60" />
      <div className="absolute inset-x-0 top-[36%] text-center font-mono text-[clamp(5px,0.6vw,9px)] tracking-[0.3em] text-gold/60">DEFENDANT</div>
    </div>
  );
}

function CounselTable({ side, label }: { side: "left" | "right"; label: string }) {
  return (
    <div className={cn("absolute top-[89%] z-[6] h-[13%] w-[33%]", side === "left" ? "left-[0%]" : "right-[0%]")}>
      <div className="absolute inset-0 rounded-t-md bg-[linear-gradient(180deg,#2a211b,#100c0a)] shadow-[0_-8px_24px_rgba(0,0,0,0.5)]" />
      <div className="absolute inset-x-0 top-0 h-[7%] rounded-t-md bg-gold/55" />
      <div className="absolute inset-x-0 top-[26%] text-center font-mono text-[clamp(5px,0.65vw,9px)] uppercase tracking-[0.3em] text-gold/60">{label}</div>
    </div>
  );
}
