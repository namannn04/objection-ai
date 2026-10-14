"use client";

import { useEffect, useRef } from "react";
import type { Expression } from "./palette";

export type AmplitudeSource = () => number;

/** Drives a mouth's openness straight from the audio analyser — no React renders per frame. */
export function useMouth(source: AmplitudeSource | null, speaking: boolean, base: number, range: number) {
  const ref = useRef<SVGEllipseElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!speaking || !source) {
      el.setAttribute("ry", String(base));
      return;
    }
    let raf = 0;
    let smooth = 0;
    const tick = () => {
      const a = Math.min(1, source() * 5.5);
      smooth += (a - smooth) * (a > smooth ? 0.55 : 0.25);
      el.setAttribute("ry", (base + smooth * range).toFixed(2));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [source, speaking, base, range]);
  return ref;
}

interface EyeProps {
  cx: number;
  cy: number;
  expression: Expression;
  side: -1 | 1;
  white: string;
  pupil: string;
  glow?: boolean;
}

export function Eye({ cx, cy, expression, side, white, pupil, glow }: EyeProps) {
  if (expression === "laughing") {
    return <path d={`M${cx - 6} ${cy + 1} Q${cx} ${cy - 6} ${cx + 6} ${cy + 1}`} stroke={glow ? white : pupil} strokeWidth={2.6} fill="none" strokeLinecap="round" />;
  }
  const big = expression === "surprised";
  const small = expression === "nervous";
  const rx = big ? 7 : small ? 4.5 : 6;
  const ry = big ? 7.5 : expression === "smug" ? 3 : small ? 4.5 : 5.2;
  const look = expression === "smug" ? side * 1.5 : expression === "confused" ? 1.5 : 0;
  return (
    <g className="eye">
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={white} />
      {!glow && <circle cx={cx + look} cy={cy + (expression === "sad" ? 1 : 0)} r={big ? 2.6 : 3} fill={pupil} />}
      {!glow && <circle cx={cx + look + 1} cy={cy - 1} r={0.9} fill="#fff" opacity={0.8} />}
      {/* eyelid for blinking */}
      <rect className="lid" x={cx - rx - 1} y={cy - ry - 1} width={rx * 2 + 2} height={ry * 2 + 2} fill="currentColor" />
    </g>
  );
}

export function Brow({ x1, x2, y, expression, side, color, width = 3 }: {
  x1: number; x2: number; y: number; expression: Expression; side: -1 | 1; color: string; width?: number;
}) {
  // side -1 = left brow, 1 = right brow. Inner end is the one nearer the face centre.
  const inner = side === -1 ? x2 : x1;
  const outer = side === -1 ? x1 : x2;
  let yi = y;
  let yo = y;
  switch (expression) {
    case "angry":
    case "stern":
      yi = y + (expression === "angry" ? 5 : 3);
      yo = y - 1;
      break;
    case "surprised":
      yi = y - 6;
      yo = y - 5;
      break;
    case "sad":
    case "nervous":
      yi = y - 4;
      yo = y + 2;
      break;
    case "confused":
      if (side === 1) {
        yi = y - 6;
        yo = y - 4;
      } else {
        yi = y + 2;
      }
      break;
    case "smug":
      if (side === 1) yo = y - 4;
      break;
  }
  return <line x1={outer} y1={yo} x2={inner} y2={yi} stroke={color} strokeWidth={width} strokeLinecap="round" className="brow" />;
}

/** Static mouth for non-speaking expressions; speaking uses the animated ellipse. */
export function Mouth({ cx, cy, expression, color, speaking, mouthRef, width = 9 }: {
  cx: number; cy: number; expression: Expression; color: string; speaking: boolean;
  mouthRef: React.Ref<SVGEllipseElement>; width?: number;
}) {
  if (speaking) {
    return <ellipse ref={mouthRef} cx={cx} cy={cy} rx={width} ry={1.5} fill={color} />;
  }
  switch (expression) {
    case "surprised":
      return <ellipse cx={cx} cy={cy + 1} rx={width * 0.55} ry={6} fill={color} />;
    case "laughing":
      return <path d={`M${cx - width} ${cy - 2} Q${cx} ${cy + 12} ${cx + width} ${cy - 2} Z`} fill={color} />;
    case "smug":
      return <path d={`M${cx - width} ${cy + 1} Q${cx + 2} ${cy + 4} ${cx + width} ${cy - 4}`} stroke={color} strokeWidth={2.6} fill="none" strokeLinecap="round" />;
    case "angry":
    case "sad":
      return <path d={`M${cx - width * 0.8} ${cy + 3} Q${cx} ${cy - 4} ${cx + width * 0.8} ${cy + 3}`} stroke={color} strokeWidth={2.6} fill="none" strokeLinecap="round" />;
    case "nervous":
      return <path d={`M${cx - width} ${cy} q3 -3 6 0 t6 0 t6 0`} stroke={color} strokeWidth={2.2} fill="none" strokeLinecap="round" />;
    case "confused":
      return <path d={`M${cx - width * 0.8} ${cy + 1} L${cx + width * 0.8} ${cy - 2}`} stroke={color} strokeWidth={2.6} strokeLinecap="round" />;
    default:
      return <path d={`M${cx - width * 0.8} ${cy} Q${cx} ${cy + 2.5} ${cx + width * 0.8} ${cy}`} stroke={color} strokeWidth={2.6} fill="none" strokeLinecap="round" />;
  }
}

export function SweatDrop({ x, y }: { x: number; y: number }) {
  return (
    <path
      className="sweat"
      d={`M${x} ${y} q-5 9 0 12 q5 -3 0 -12z`}
      fill="#9fd3ff"
      stroke="#e8f6ff"
      strokeWidth={0.8}
      opacity={0.9}
    />
  );
}
