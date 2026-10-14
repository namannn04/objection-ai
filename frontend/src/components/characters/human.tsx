"use client";

import { useId } from "react";
import { Brow, Eye, Mouth, SweatDrop, useMouth, type AmplitudeSource } from "./face-parts";
import { palette, type Expression } from "./palette";

type HairStyle = "wig" | "bob" | "quiff" | "ponytail" | "crop";

export interface HumanLook {
  skin: string;
  skinShade: string;
  hair: string;
  hairStyle: HairStyle;
  suit: string;
  accessory: string;
}

// The recurring ensemble. Per-case humans fall back to a neutral look.
export const LOOKS: Record<string, HumanLook> = {
  judge: { skin: "#e7c7a4", skinShade: "#b98f6a", hair: "#efe9dd", hairStyle: "wig", suit: "#111", accessory: "wig" },
  prosecutor: { skin: "#d39a74", skinShade: "#9c6646", hair: "#151012", hairStyle: "bob", suit: "burgundy", accessory: "glasses" },
  defense: { skin: "#8e5b3c", skinShade: "#5e3a24", hair: "#21160f", hairStyle: "quiff", suit: "teal", accessory: "bowtie" },
  reporter: { skin: "#f0d0b1", skinShade: "#c39a76", hair: "#83402a", hairStyle: "ponytail", suit: "ivory", accessory: "headset" },
};

const FALLBACK: HumanLook = { skin: "#c99a78", skinShade: "#946649", hair: "#2a1d16", hairStyle: "crop", suit: "slate", accessory: "tie" };

function Hair({ style, color, back }: { style: HairStyle; color: string; back: boolean }) {
  if (style === "wig") {
    const curls = [62, 80, 98, 116, 134];
    return back ? (
      <g fill={color}>
        {curls.map((y) => (
          <g key={y}>
            <circle cx={58} cy={y} r={12} />
            <circle cx={142} cy={y} r={12} />
          </g>
        ))}
        <ellipse cx={100} cy={146} rx={46} ry={10} />
      </g>
    ) : (
      <g fill={color}>
        <path d="M58 76 Q60 38 100 36 Q140 38 142 76 Q128 56 100 56 Q72 56 58 76Z" />
        {[70, 86, 102, 118, 132].map((x) => <circle key={x} cx={x} cy={50} r={8} />)}
        <path d="M60 78 q8 -10 18 -6" stroke="#cfc6b4" strokeWidth={2} fill="none" />
        <path d="M140 78 q-8 -10 -18 -6" stroke="#cfc6b4" strokeWidth={2} fill="none" />
      </g>
    );
  }
  if (style === "bob") {
    return back ? (
      <path d="M56 112 Q52 46 100 42 Q148 46 144 112 L144 128 Q130 122 128 104 L72 104 Q70 122 56 128Z" fill={color} />
    ) : (
      <path d="M62 82 Q66 48 100 46 Q134 48 138 82 Q118 62 100 74 Q86 60 62 82Z" fill={color} />
    );
  }
  if (style === "quiff") {
    return back ? null : (
      <g fill={color}>
        <path d="M61 88 Q56 50 96 44 Q140 40 140 86 Q132 64 112 62 Q120 46 96 50 Q74 56 68 76Z" />
        <path d="M96 50 Q112 30 128 46 Q114 40 104 52Z" />
      </g>
    );
  }
  if (style === "ponytail") {
    return back ? (
      <g fill={color}>
        <ellipse cx={146} cy={70} rx={16} ry={22} transform="rotate(25 146 70)" />
        <path d="M60 96 Q56 46 100 44 Q144 46 140 96Z" />
      </g>
    ) : (
      <path d="M62 84 Q66 50 100 48 Q136 50 140 82 Q122 58 96 64 Q76 68 62 84Z" fill={color} />
    );
  }
  return back ? null : <path d="M62 80 Q64 48 100 46 Q136 48 138 80 Q120 60 100 62 Q80 60 62 80Z" fill={color} />;
}

export function HumanPortrait({
  characterKey, expression, speaking, amplitude, palette: pal,
}: {
  characterKey: string; expression: Expression; speaking: boolean; amplitude: AmplitudeSource | null; palette?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const look = LOOKS[characterKey] ?? { ...FALLBACK, suit: pal ?? FALLBACK.suit };
  const suit = look.suit.startsWith("#") ? { base: look.suit, dark: "#000", light: "#333" } : palette(look.suit);
  const mouthRef = useMouth(amplitude, speaking, 1.5, 7.5);
  const browColor = look.hairStyle === "wig" ? "#d9d2c4" : look.hair;

  return (
    <svg viewBox="0 0 200 220" className="h-full w-full overflow-visible" style={{ color: look.skin }} aria-hidden>
      <defs>
        <clipPath id={`head-${uid}`}>
          <ellipse cx={100} cy={92} rx={38} ry={44} />
        </clipPath>
        <linearGradient id={`suit-${uid}`} x1="0" x2="1">
          <stop offset="0" stopColor={suit.light} />
          <stop offset="0.35" stopColor={suit.base} />
          <stop offset="1" stopColor={suit.dark} />
        </linearGradient>
      </defs>

      <g className="breathe">
        <Hair style={look.hairStyle} color={look.hair} back />
        {/* torso */}
        <path d="M18 222 C22 176 50 160 100 158 C150 160 178 176 182 222Z" fill={`url(#suit-${uid})`} />
        {look.hairStyle === "wig" && <path d="M70 160 L100 222 L130 160 Q100 170 70 160Z" fill="#d6ae62" opacity={0.85} />}
        <path d="M84 160 L100 198 L116 160Z" fill="#f5f0e6" />
        <path d="M84 160 L100 198 L72 176Z" fill={suit.dark} opacity={0.9} />
        <path d="M116 160 L100 198 L128 176Z" fill={suit.dark} opacity={0.9} />
        {look.accessory === "tie" && <path d="M96 166 L104 166 L106 194 L100 202 L94 194Z" fill="#6b202a" />}
        {look.accessory === "bowtie" && (
          <g fill="#d6ae62">
            <path d="M100 168 L86 161 L86 175Z" />
            <path d="M100 168 L114 161 L114 175Z" />
            <circle cx={100} cy={168} r={3} />
          </g>
        )}
        {/* neck */}
        <rect x={88} y={124} width={24} height={40} rx={8} fill={look.skinShade} />
        {/* ears */}
        <ellipse cx={62} cy={96} rx={6} ry={9} fill={look.skinShade} />
        <ellipse cx={138} cy={96} rx={6} ry={9} fill={look.skinShade} />
        {/* head */}
        <ellipse cx={100} cy={92} rx={38} ry={44} fill={look.skin} />
        {/* chiaroscuro: shadow side + gold rim light */}
        <g clipPath={`url(#head-${uid})`}>
          <path d="M104 40 Q132 70 120 140 L160 140 L160 40Z" fill="#000" opacity={0.22} />
        </g>
        <path d="M68 62 A38 44 0 0 0 64 118" stroke="#d6ae62" strokeWidth={2} fill="none" opacity={0.55} />
        {/* face */}
        <Eye cx={86} cy={93} expression={expression} side={-1} white="#f8f4ec" pupil="#1a1210" />
        <Eye cx={114} cy={93} expression={expression} side={1} white="#f8f4ec" pupil="#1a1210" />
        <Brow x1={77} x2={94} y={81} expression={expression} side={-1} color={browColor} width={look.hairStyle === "wig" ? 4 : 3} />
        <Brow x1={106} x2={123} y={81} expression={expression} side={1} color={browColor} width={look.hairStyle === "wig" ? 4 : 3} />
        <path d="M100 96 Q96 106 101 108" stroke={look.skinShade} strokeWidth={2} fill="none" strokeLinecap="round" />
        <Mouth cx={100} cy={118} expression={expression} color="#2b1215" speaking={speaking} mouthRef={mouthRef} />
        {(expression === "laughing" || expression === "smug") && (
          <>
            <ellipse cx={78} cy={108} rx={6} ry={3} fill="#e0705f" opacity={0.25} />
            <ellipse cx={122} cy={108} rx={6} ry={3} fill="#e0705f" opacity={0.25} />
          </>
        )}
        <Hair style={look.hairStyle} color={look.hair} back={false} />
        {look.accessory === "glasses" && (
          <g stroke="#d6ae62" strokeWidth={1.8} fill="rgba(255,255,255,0.06)">
            <rect x={75} y={85} width={22} height={16} rx={5} />
            <rect x={103} y={85} width={22} height={16} rx={5} />
            <path d="M97 92 Q100 89 103 92" fill="none" />
          </g>
        )}
        {look.accessory === "headset" && (
          <g stroke="#202020" strokeWidth={4} fill="none">
            <path d="M60 96 Q60 40 100 40 Q140 40 140 96" />
            <rect x={132} y={88} width={12} height={20} rx={4} fill="#202020" />
            <path d="M138 106 Q132 124 112 122" strokeWidth={2.5} />
            <circle cx={111} cy={122} r={3} fill="#d6ae62" stroke="none" />
          </g>
        )}
        {expression === "nervous" && <SweatDrop x={134} y={70} />}
      </g>
    </svg>
  );
}
