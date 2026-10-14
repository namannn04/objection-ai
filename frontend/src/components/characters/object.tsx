"use client";

import { useId } from "react";
import { Brow, Eye, Mouth, SweatDrop, useMouth, type AmplitudeSource } from "./face-parts";
import { palette, type Expression } from "./palette";

type Shape = "block" | "monitor" | "rack" | "calendar" | "router" | "clock" | "battery" | "mug" | "orb" | "printer" | "bubble";

const SHAPE_HINTS: [RegExp, Shape][] = [
  [/server|prod|database|cloud/i, "rack"],
  [/console|terminal|screen|monitor|laptop|computer/i, "monitor"],
  [/monday|tuesday|wednesday|thursday|friday|saturday|sunday|calendar|weekend|deadline/i, "calendar"],
  [/wi-?fi|router|internet|ethernet|cable|bluetooth/i, "router"],
  [/clock|alarm|snooze|time|minute/i, "clock"],
  [/battery|charger|power/i, "battery"],
  [/coffee|mug|tea|cup/i, "mug"],
  [/printer|fax|paper|ink/i, "printer"],
  [/chat|message|text|email|meme/i, "bubble"],
  [/sense|nerve|feeling|vibe|night|concept/i, "orb"],
];

export function shapeFor(name: string, glyph: string): Shape {
  for (const [re, shape] of SHAPE_HINTS) if (re.test(name) || re.test(glyph)) return shape;
  return "block";
}

interface Props {
  name: string;
  glyph: string;
  paletteName: string;
  expression: Expression;
  speaking: boolean;
  amplitude: AmplitudeSource | null;
}

/** Objects and concepts on trial: a body that fits what they are, with a lit screen-face. */
export function ObjectPortrait({ name, glyph, paletteName, expression, speaking, amplitude }: Props) {
  const uid = useId().replace(/:/g, "");
  const p = palette(paletteName);
  const shape = shapeFor(name, glyph);
  const mouthRef = useMouth(amplitude, speaking, 1.4, 7);
  const face = { y: shape === "clock" || shape === "orb" ? 104 : shape === "calendar" ? 118 : 102 };
  const glyphText = glyph.length > 4 ? glyph.slice(0, 4) : glyph;
  const emojiGlyph = /\p{Extended_Pictographic}/u.test(glyphText);

  return (
    <svg viewBox="0 0 200 220" className="h-full w-full overflow-visible" style={{ color: "#141414" }} aria-hidden>
      <defs>
        <linearGradient id={`body-${uid}`} x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor={p.light} />
          <stop offset="0.45" stopColor={p.base} />
          <stop offset="1" stopColor={p.dark} />
        </linearGradient>
        <radialGradient id={`screen-${uid}`} cx="0.4" cy="0.35" r="0.9">
          <stop offset="0" stopColor="#262626" />
          <stop offset="1" stopColor="#0c0c0c" />
        </radialGradient>
      </defs>
      <g className="breathe">
        <Body shape={shape} fill={`url(#body-${uid})`} dark={p.dark} light={p.light} />
        {/* screen face */}
        {shape === "clock" || shape === "orb" ? (
          <circle cx={100} cy={face.y} r={44} fill={`url(#screen-${uid})`} />
        ) : (
          <rect x={56} y={face.y - 34} width={88} height={66} rx={14} fill={`url(#screen-${uid})`} />
        )}
        <g style={{ filter: `drop-shadow(0 0 3px ${p.light})` }}>
          <Eye cx={84} cy={face.y - 8} expression={expression} side={-1} white="#f5f0e6" pupil="#f5f0e6" glow />
          <Eye cx={116} cy={face.y - 8} expression={expression} side={1} white="#f5f0e6" pupil="#f5f0e6" glow />
          <Brow x1={74} x2={92} y={face.y - 21} expression={expression} side={-1} color="#f5f0e6" width={2.4} />
          <Brow x1={108} x2={126} y={face.y - 21} expression={expression} side={1} color="#f5f0e6" width={2.4} />
          <Mouth cx={100} cy={face.y + 14} expression={expression} color="#f5f0e6" speaking={speaking} mouthRef={mouthRef} width={8} />
        </g>
        {glyphText && (
          <text
            x={100}
            y={shape === "calendar" ? 66 : shape === "rack" ? 156 : shape === "block" || shape === "battery" ? 164 : 194}
            textAnchor="middle"
            fontFamily={emojiGlyph ? undefined : "var(--font-geist-mono), monospace"}
            fontWeight={700}
            fontSize={glyphText.length > 3 ? 18 : 24}
            fill={shape === "calendar" ? "#f5f0e6" : shape === "printer" ? p.dark : p.light}
            letterSpacing={1}
          >
            {glyphText}
          </text>
        )}
        {expression === "nervous" && <SweatDrop x={146} y={face.y - 30} />}
      </g>
    </svg>
  );
}

function Body({ shape, fill, dark, light }: { shape: Shape; fill: string; dark: string; light: string }) {
  switch (shape) {
    case "rack":
      return (
        <g>
          <rect x={40} y={50} width={120} height={168} rx={10} fill={fill} />
          {[176, 192, 208].map((y) => (
            <g key={y}>
              <rect x={50} y={y - 6} width={100} height={10} rx={3} fill={dark} />
              <circle cx={140} cy={y - 1} r={2.2} fill={y === 192 ? "#e05050" : "#7be07b"} className="led" />
            </g>
          ))}
        </g>
      );
    case "monitor":
      return (
        <g>
          <rect x={30} y={52} width={140} height={110} rx={12} fill={fill} />
          <rect x={88} y={162} width={24} height={22} fill={dark} />
          <rect x={62} y={182} width={76} height={14} rx={6} fill={fill} />
        </g>
      );
    case "calendar":
      return (
        <g>
          <rect x={36} y={44} width={128} height={160} rx={12} fill="#f1ebdf" />
          <rect x={36} y={44} width={128} height={38} rx={12} fill={fill} />
          <rect x={36} y={70} width={128} height={12} fill={fill} />
          {[66, 100, 134].map((x) => <rect key={x} x={x - 4} y={36} width={8} height={18} rx={4} fill={dark} />)}
          {[0, 1, 2, 3, 4].map((i) => <rect key={i} x={50 + i * 21} y={186} width={13} height={8} rx={2} fill={light} opacity={0.5} />)}
        </g>
      );
    case "router":
      return (
        <g>
          <line x1={62} y1={60} x2={50} y2={20} stroke={dark} strokeWidth={6} strokeLinecap="round" />
          <line x1={138} y1={60} x2={150} y2={20} stroke={dark} strokeWidth={6} strokeLinecap="round" />
          <rect x={32} y={58} width={136} height={112} rx={18} fill={fill} />
          {[0, 1, 2, 3].map((i) => <circle key={i} cx={70 + i * 20} cy={158} r={3} fill={i < 2 ? "#7be07b" : "#e0a040"} className="led" />)}
          <rect x={60} y={176} width={80} height={24} rx={8} fill={dark} />
        </g>
      );
    case "clock":
      return (
        <g>
          <circle cx={58} cy={50} r={16} fill={dark} />
          <circle cx={142} cy={50} r={16} fill={dark} />
          <circle cx={100} cy={104} r={64} fill={fill} />
          <line x1={64} y1={160} x2={54} y2={186} stroke={dark} strokeWidth={8} strokeLinecap="round" />
          <line x1={136} y1={160} x2={146} y2={186} stroke={dark} strokeWidth={8} strokeLinecap="round" />
          <rect x={60} y={176} width={80} height={24} rx={8} fill={dark} opacity={0.6} />
        </g>
      );
    case "battery":
      return (
        <g>
          <rect x={84} y={30} width={32} height={18} rx={4} fill={dark} />
          <rect x={44} y={44} width={112} height={164} rx={16} fill={fill} />
          <rect x={52} y={200} width={20} height={6} rx={3} fill="#e05050" className="led" />
        </g>
      );
    case "mug":
      return (
        <g>
          <path d="M152 86 q34 4 30 40 q-4 32 -30 30" stroke={dark} strokeWidth={12} fill="none" />
          <path d="M40 54 L160 54 L152 196 Q100 212 48 196Z" fill={fill} />
          <path d="M80 38 q-6 -12 2 -20 M100 38 q-6 -12 2 -20 M120 38 q-6 -12 2 -20" stroke={light} strokeWidth={3} fill="none" opacity={0.6} className="steam" />
        </g>
      );
    case "printer":
      return (
        <g>
          <rect x={56} y={30} width={88} height={34} rx={4} fill="#f1ebdf" />
          <rect x={28} y={56} width={144} height={130} rx={14} fill={fill} />
          <rect x={50} y={176} width={100} height={22} rx={3} fill="#f1ebdf" />
        </g>
      );
    case "bubble":
      return <path d="M30 60 Q30 40 50 40 L150 40 Q170 40 170 60 L170 160 Q170 180 150 180 L80 180 L50 206 L56 180 L50 180 Q30 180 30 160Z" fill={fill} />;
    case "orb":
      return (
        <g>
          <circle cx={100} cy={104} r={70} fill={fill} opacity={0.35} />
          <circle cx={100} cy={104} r={58} fill={fill} />
          <ellipse cx={100} cy={196} rx={40} ry={8} fill={dark} opacity={0.6} />
        </g>
      );
    default:
      return (
        <g>
          <rect x={34} y={44} width={132} height={164} rx={22} fill={fill} />
          <rect x={46} y={56} width={22} height={6} rx={3} fill={light} opacity={0.6} />
        </g>
      );
  }
}
