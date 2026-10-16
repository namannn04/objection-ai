"use client";

import { Html, RoundedBox } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AmplitudeSource } from "@/components/characters/face-parts";
import { LOOKS } from "@/components/characters/human";
import { shapeFor } from "@/components/characters/object";
import { REACTION_TO_EXPRESSION, expressionFor, palette, type Expression } from "@/components/characters/palette";
import type { CharacterInfo, Reaction } from "@/lib/types";
import { labelTexture } from "./textures";

type V3 = [number, number, number];

/** Stylised scale: a touch larger than life so faces read on camera. */
export const FIGURE_SCALE = 1.35;
const HEAD_SCALE = 1.28;

const MARK: Partial<Record<Reaction, string>> = {
  gasp: "!", shocked: "!!", confused: "?", laugh: "ha", angry: "#", sweat: "…", facepalm: "ugh", smirk: "heh", nod: "mm",
};

export interface FigureProps {
  character: CharacterInfo;
  position: V3;
  speaking: boolean;
  emotion?: string;
  reaction?: Reaction | null;
  dimmed: boolean;
  amplitude: AmplitudeSource | null;
  lookAt: V3 | null; // where the current speaker is
  seed?: number;
  plate?: string;
}

/** Brow angles (inner-end raise, outer-end raise) and eye openness per expression. */
const FACE: Record<Expression, { brow: [number, number]; eye: number; smile: number }> = {
  neutral: { brow: [0, 0], eye: 1, smile: 0.15 },
  stern: { brow: [-0.35, 0.1], eye: 0.85, smile: -0.1 },
  angry: { brow: [-0.6, 0.15], eye: 0.8, smile: -0.4 },
  surprised: { brow: [0.45, 0.35], eye: 1.35, smile: 0 },
  confused: { brow: [0.4, -0.2], eye: 1.05, smile: -0.1 },
  laughing: { brow: [0.2, 0.1], eye: 0.25, smile: 0.9 },
  smug: { brow: [-0.15, 0.25], eye: 0.55, smile: 0.5 },
  sad: { brow: [0.5, -0.25], eye: 0.8, smile: -0.5 },
  nervous: { brow: [0.45, -0.1], eye: 1.15, smile: -0.2 },
};

const isHuman = (c: CharacterInfo) => c.visual?.kind === "human" || ["judge", "prosecutor", "defense", "reporter"].includes(c.key);

/** One animated 3D cast member. Humans get bodies and faces; objects get device bodies with screen-faces. */
export function Figure(props: FigureProps) {
  return isHuman(props.character) ? <Human {...props} /> : <Device {...props} />;
}

function useLife(props: FigureProps) {
  const { speaking, amplitude, reaction, emotion } = props;
  const expression: Expression = reaction ? REACTION_TO_EXPRESSION[reaction] : speaking ? expressionFor(emotion) : "neutral";
  const smooth = useRef(0);
  const blink = useRef(0);
  const nextBlink = useRef(2 + (props.seed ?? 0) * 0.7);
  const tick = (t: number) => {
    const a = speaking && amplitude ? Math.min(1, amplitude() * 5.5) : 0;
    smooth.current += (a - smooth.current) * (a > smooth.current ? 0.5 : 0.2);
    if (t > nextBlink.current) {
      blink.current = 1;
      nextBlink.current = t + 2.5 + ((props.seed ?? 0) * 1.37 + t) % 3;
    }
    blink.current = Math.max(0, blink.current - 0.16);
    return { open: smooth.current, blink: blink.current };
  };
  return { expression, tick };
}

function damp(obj: THREE.Object3D, key: "x" | "y" | "z", target: number, dt: number, lambda = 6) {
  obj.rotation[key] = THREE.MathUtils.damp(obj.rotation[key], target, lambda, dt);
}

function ReactionChip({ reaction, y }: { reaction?: Reaction | null; y: number }) {
  if (!reaction || !MARK[reaction]) return null;
  return (
    <Html position={[0.28, y, 0]} center zIndexRange={[20, 0]}>
      <span className="pointer-events-none select-none rounded-full border border-gold/60 bg-ink/90 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-gold">
        {MARK[reaction]}
      </span>
    </Html>
  );
}

// ── humans ────────────────────────────────────────────────────────────────

function Human(props: FigureProps) {
  const { character, position, dimmed, lookAt, reaction, seed = 0 } = props;
  const v = character.visual;
  const look = LOOKS[character.key] ?? (v?.hair
    ? { skin: "#c08a64", skinShade: "#8a5b3d", hair: v.hair === "balding" ? "#3a3530" : "#1c1410", hairStyle: v.hair,
        suit: v.palette ?? "slate", accessory: v.accessory ?? "none" }
    : { skin: "#c99a78", skinShade: "#946649", hair: "#2a1d16", hairStyle: "crop", suit: v?.palette ?? "slate", accessory: "tie" });
  const suitCol = look.suit.startsWith("#") ? look.suit : palette(look.suit).base;
  const judge = character.key === "judge";
  const saree = v?.attire === "saree";
  const { expression, tick } = useLife(props);
  const face = FACE[expression];

  const root = useRef<THREE.Group>(null);
  const head = useRef<THREE.Group>(null);
  const torso = useRef<THREE.Group>(null);
  const armR = useRef<THREE.Group>(null);
  const armL = useRef<THREE.Group>(null);
  const mouth = useRef<THREE.Mesh>(null);
  const lids = useRef<THREE.Group>(null);
  const browL = useRef<THREE.Mesh>(null);
  const browR = useRef<THREE.Mesh>(null);
  const mats = useMemo(() => ({
    skin: new THREE.MeshStandardMaterial({ color: look.skin, roughness: 0.62 }),
    shade: new THREE.MeshStandardMaterial({ color: look.skinShade, roughness: 0.7 }),
    hair: new THREE.MeshStandardMaterial({ color: look.hair, roughness: judge ? 0.95 : 0.5, metalness: judge ? 0 : 0.05 }),
    suit: new THREE.MeshStandardMaterial({ color: suitCol, roughness: 0.7 }),
    suitDark: new THREE.MeshStandardMaterial({ color: new THREE.Color(suitCol).multiplyScalar(0.55), roughness: 0.75 }),
    shirt: new THREE.MeshStandardMaterial({ color: "#efe8da", roughness: 0.8 }),
    gold: new THREE.MeshStandardMaterial({ color: "#d6ae62", metalness: 0.85, roughness: 0.3 }),
    eyeWhite: new THREE.MeshStandardMaterial({ color: "#f6f1e8", roughness: 0.3 }),
    pupil: new THREE.MeshStandardMaterial({ color: "#1a1210", roughness: 0.2 }),
    mouth: new THREE.MeshBasicMaterial({ color: "#2b1215" }),
    brow: new THREE.MeshStandardMaterial({ color: judge ? "#d9d2c4" : look.hair, roughness: 0.8 }),
    pallu: new THREE.MeshStandardMaterial({ color: "#8e1f3a", roughness: 0.55, metalness: 0.08 }),
    bindi: new THREE.MeshBasicMaterial({ color: "#c0122a" }),
  }), [look.skin, look.skinShade, look.hair, suitCol, judge]);

  useFrame(({ clock }, dt) => {
    const t = clock.elapsedTime + seed * 1.3;
    const { open, blink } = tick(clock.elapsedTime);
    if (!root.current || !head.current) return;
    // look at the speaker (or the audience when talking)
    let yaw = 0;
    let pitch = 0;
    if (props.speaking) {
      yaw = Math.sin(t * 0.7) * 0.18;
    } else if (lookAt) {
      const dx = lookAt[0] - position[0];
      const dz = lookAt[2] - position[2];
      yaw = THREE.MathUtils.clamp(Math.atan2(dx, dz), -1.1, 1.1);
      pitch = THREE.MathUtils.clamp(-(lookAt[1] - (position[1] + 1.69 * FIGURE_SCALE)) * 0.15, -0.25, 0.25);
    }
    damp(head.current, "y", yaw, dt, 4);
    damp(head.current, "x", pitch + (props.speaking ? Math.sin(t * 6) * open * 0.06 : 0), dt, 6);
    damp(head.current, "z", reaction === "confused" ? 0.18 : Math.sin(t * 0.5) * 0.02, dt, 4);
    if (torso.current) torso.current.scale.y = 1 + Math.sin(t * 1.6) * 0.008;
    root.current.position.y = position[1] + (reaction === "gasp" || reaction === "shocked" ? Math.max(0, Math.sin(t * 10)) * 0.04 : 0);
    // gestures while speaking
    if (armR.current) {
      const g = props.speaking ? -0.9 - Math.sin(t * 2.6) * 0.35 * (0.4 + open) : reaction === "facepalm" ? -2.2 : -0.12;
      damp(armR.current, "x", g, dt, 5);
      damp(armR.current, "z", props.speaking ? -0.25 : 0.05, dt, 5);
    }
    if (armL.current) damp(armL.current, "x", props.speaking && open > 0.5 ? -0.6 : -0.1, dt, 4);
    if (mouth.current) {
      mouth.current.scale.set(1 + open * 0.15, props.speaking ? 0.25 + open * 1.6 : 0.18, 1);
      mouth.current.position.y = -0.065 + (props.speaking ? 0 : face.smile * 0.004);
    }
    if (lids.current) lids.current.scale.y = Math.max(blink, 1 - Math.min(1, face.eye)) || 0.001;
    if (browL.current && browR.current) {
      browL.current.rotation.z = -face.brow[0] * 0.6;
      browR.current.rotation.z = face.brow[0] * 0.6;
      browL.current.position.y = browR.current.position.y = 0.068 + (face.brow[0] + face.brow[1]) * 0.012;
    }
    const tint = dimmed ? 0.55 : 1;
    for (const m of [mats.skin, mats.suit, mats.hair, mats.shirt]) {
      const base = m === mats.skin ? look.skin : m === mats.suit ? suitCol : m === mats.hair ? look.hair : "#efe8da";
      m.color.lerp(new THREE.Color(base).multiplyScalar(tint), Math.min(1, dt * 4));
    }
  });

  return (
    <group ref={root} position={position} scale={FIGURE_SCALE}>
      {/* torso */}
      <group ref={torso} position={[0, 0, 0]}>
        <mesh position={[0, 1.18, 0]} scale={[1, 1, 0.62]} material={judge ? mats.suitDark : mats.suit} castShadow>
          <capsuleGeometry args={[0.2, 0.42, 6, 16]} />
        </mesh>
        <mesh position={[0, 1.4, 0]} rotation={[0, 0, Math.PI / 2]} scale={[1, 1, 0.7]} material={judge ? mats.suitDark : mats.suit} castShadow>
          <capsuleGeometry args={[0.1, 0.34, 6, 12]} />
        </mesh>
        {saree ? (
          <>
            {/* pallu: draped over the left shoulder and across the chest, gold border */}
            <mesh position={[0.015, 1.2, 0.128]} rotation={[-0.08, 0, 0.55]} material={mats.pallu}><boxGeometry args={[0.15, 0.62, 0.02]} /></mesh>
            <mesh position={[0.068, 1.215, 0.136]} rotation={[-0.08, 0, 0.55]} material={mats.gold}><boxGeometry args={[0.018, 0.6, 0.01]} /></mesh>
            <mesh position={[-0.2, 1.4, 0.0]} rotation={[0, 0, -0.3]} scale={[1, 1, 0.9]} material={mats.pallu}><capsuleGeometry args={[0.07, 0.12, 4, 10]} /></mesh>
            {/* skirt flare */}
            <mesh position={[0, 0.86, 0]} scale={[1, 1, 0.75]} material={mats.suit} castShadow><cylinderGeometry args={[0.2, 0.27, 0.36, 20]} /></mesh>
            <mesh position={[0, 0.69, 0]} scale={[1, 1, 0.75]} material={mats.gold}><cylinderGeometry args={[0.272, 0.272, 0.025, 20]} /></mesh>
          </>
        ) : (
          /* shirt V + lapels */
          <mesh position={[0, 1.36, 0.118]} rotation={[-0.12, 0, Math.PI]} material={mats.shirt}>
            <coneGeometry args={[0.07, 0.24, 3]} />
          </mesh>
        )}
        {saree ? null : judge ? (
          <mesh position={[0, 1.44, 0.03]} rotation={[Math.PI / 2, 0, 0]} material={mats.gold}>
            <torusGeometry args={[0.12, 0.022, 8, 24]} />
          </mesh>
        ) : (
          <>
            <mesh position={[-0.07, 1.33, 0.12]} rotation={[0, 0.2, -0.35]} material={mats.suitDark}><boxGeometry args={[0.05, 0.22, 0.02]} /></mesh>
            <mesh position={[0.07, 1.33, 0.12]} rotation={[0, -0.2, 0.35]} material={mats.suitDark}><boxGeometry args={[0.05, 0.22, 0.02]} /></mesh>
          </>
        )}
        {look.accessory === "tie" && (
          <mesh position={[0, 1.3, 0.13]} material={new THREE.MeshStandardMaterial({ color: "#6b202a", roughness: 0.6 })}><boxGeometry args={[0.04, 0.18, 0.01]} /></mesh>
        )}
        {look.accessory === "bowtie" && (
          <group position={[0, 1.44, 0.13]}>
            <mesh rotation={[0, 0, Math.PI / 2]} position={[-0.03, 0, 0]} material={mats.gold}><coneGeometry args={[0.025, 0.05, 3]} /></mesh>
            <mesh rotation={[0, 0, -Math.PI / 2]} position={[0.03, 0, 0]} material={mats.gold}><coneGeometry args={[0.025, 0.05, 3]} /></mesh>
          </group>
        )}
        {/* arms: pivot at the shoulder */}
        <group ref={armL} position={[-0.27, 1.4, 0]}>
          <mesh position={[0, -0.2, 0]} material={judge ? mats.suitDark : mats.suit} castShadow><capsuleGeometry args={[0.065, 0.3, 4, 10]} /></mesh>
          <mesh position={[0, -0.42, 0.02]} material={mats.skin}><sphereGeometry args={[0.055, 12, 10]} /></mesh>
        </group>
        <group ref={armR} position={[0.27, 1.4, 0]}>
          <mesh position={[0, -0.2, 0]} material={judge ? mats.suitDark : mats.suit} castShadow><capsuleGeometry args={[0.065, 0.3, 4, 10]} /></mesh>
          <mesh position={[0, -0.42, 0.02]} material={mats.skin}><sphereGeometry args={[0.055, 12, 10]} /></mesh>
        </group>
        {/* neck */}
        <mesh position={[0, 1.52, 0]} material={mats.shade}><cylinderGeometry args={[0.05, 0.06, 0.12, 12]} /></mesh>
      </group>

      {/* head */}
      <group ref={head} position={[0, 1.69, 0]} scale={HEAD_SCALE}>
        <mesh scale={[0.92, 1.08, 0.97]} material={mats.skin} castShadow><sphereGeometry args={[0.13, 32, 24]} /></mesh>
        <mesh position={[-0.12, 0, 0]} scale={[0.5, 1, 0.8]} material={mats.shade}><sphereGeometry args={[0.035, 10, 8]} /></mesh>
        <mesh position={[0.12, 0, 0]} scale={[0.5, 1, 0.8]} material={mats.shade}><sphereGeometry args={[0.035, 10, 8]} /></mesh>
        <mesh position={[0, -0.015, 0.125]} scale={[0.8, 1.1, 1]} material={mats.shade}><sphereGeometry args={[0.022, 10, 8]} /></mesh>
        {/* eyes */}
        {[-1, 1].map((sx) => (
          <group key={sx} position={[sx * 0.045, 0.022, 0.108]}>
            <mesh scale={[1, 1, 0.55]} material={mats.eyeWhite}><sphereGeometry args={[0.022, 16, 12]} /></mesh>
            <mesh position={[0, 0, 0.011]} material={mats.pupil}><sphereGeometry args={[0.012, 12, 10]} /></mesh>
          </group>
        ))}
        {/* eyelids (blink + sleepy/smug) */}
        <group ref={lids} position={[0, 0.044, 0.112]} scale={[1, 0.001, 1]}>
          {[-1, 1].map((sx) => (
            <mesh key={sx} position={[sx * 0.045, -0.022, 0.004]} material={mats.skin}><boxGeometry args={[0.05, 0.046, 0.012]} /></mesh>
          ))}
        </group>
        {/* brows */}
        <mesh ref={browL} position={[-0.045, 0.068, 0.118]} material={mats.brow}><boxGeometry args={[0.05, judge ? 0.014 : 0.01, 0.01]} /></mesh>
        <mesh ref={browR} position={[0.045, 0.068, 0.118]} material={mats.brow}><boxGeometry args={[0.05, judge ? 0.014 : 0.01, 0.01]} /></mesh>
        {/* mouth: an ellipse that opens with the voice */}
        <mesh ref={mouth} position={[0, -0.065, 0.118]} material={mats.mouth}><circleGeometry args={[0.03, 20]} /></mesh>
        <Hair style={look.hairStyle} mat={mats.hair} />
        {v?.bindi && (
          <mesh position={[0, 0.06, 0.128]} material={mats.bindi}><circleGeometry args={[0.009, 16]} /></mesh>
        )}
        {saree && [-1, 1].map((sx) => (
          <mesh key={sx} position={[sx * 0.128, -0.045, 0.01]} material={mats.gold}><sphereGeometry args={[0.014, 10, 8]} /></mesh>
        ))}
        {v?.mustache && (
          <mesh position={[0, -0.04, 0.122]} rotation={[0.15, 0, 0]} scale={[1, 0.32, 0.45]} material={mats.hair}>
            <sphereGeometry args={[0.042, 16, 10]} />
          </mesh>
        )}
        {look.accessory === "glasses" && (
          <group position={[0, 0.022, 0.13]}>
            {[-1, 1].map((sx) => (
              <mesh key={sx} position={[sx * 0.045, 0, 0]} material={mats.gold}><torusGeometry args={[0.03, 0.004, 6, 20]} /></mesh>
            ))}
            <mesh material={mats.gold}><boxGeometry args={[0.03, 0.004, 0.004]} /></mesh>
          </group>
        )}
        {look.accessory === "headset" && (
          <group>
            <mesh position={[0, 0.04, 0]} rotation={[0, Math.PI / 2, 0]} material={new THREE.MeshStandardMaterial({ color: "#202020" })}>
              <torusGeometry args={[0.142, 0.008, 6, 24, Math.PI]} />
            </mesh>
            <mesh position={[0.13, -0.05, 0.06]} rotation={[0.2, 0.6, 0]} material={mats.gold}><cylinderGeometry args={[0.004, 0.004, 0.12]} /></mesh>
          </group>
        )}
      </group>
      <ReactionChip reaction={reaction} y={2.1} />
    </group>
  );
}

function Hair({ style, mat }: { style: string; mat: THREE.Material }) {
  if (style === "wig") {
    const curls: V3[] = [];
    for (let i = 0; i < 5; i++) {
      curls.push([-0.135, 0.06 - i * 0.07, -0.02], [0.135, 0.06 - i * 0.07, -0.02]);
    }
    return (
      <group>
        <mesh position={[0, 0.06, -0.01]} scale={[1.08, 0.75, 1.05]} material={mat}><sphereGeometry args={[0.135, 20, 14, 0, Math.PI * 2, 0, Math.PI / 1.8]} /></mesh>
        {[-0.08, 0, 0.08].map((x) => <mesh key={x} position={[x, 0.13, 0.02]} material={mat}><sphereGeometry args={[0.04, 12, 10]} /></mesh>)}
        {curls.map((p, i) => <mesh key={i} position={p} material={mat}><sphereGeometry args={[0.045, 12, 10]} /></mesh>)}
      </group>
    );
  }
  if (style === "bob") {
    return (
      <group>
        <mesh position={[0, 0.03, -0.005]} scale={[1.1, 1, 1.08]} material={mat}><sphereGeometry args={[0.135, 24, 16, 0, Math.PI * 2, 0, Math.PI / 1.9]} /></mesh>
        <mesh position={[-0.115, -0.05, 0]} scale={[0.45, 1.3, 0.95]} material={mat}><sphereGeometry args={[0.1, 14, 12]} /></mesh>
        <mesh position={[0.115, -0.05, 0]} scale={[0.45, 1.3, 0.95]} material={mat}><sphereGeometry args={[0.1, 14, 12]} /></mesh>
        <mesh position={[0.02, 0.085, 0.09]} rotation={[0.5, 0, 0.3]} scale={[1.4, 0.4, 0.6]} material={mat}><sphereGeometry args={[0.07, 14, 10]} /></mesh>
      </group>
    );
  }
  if (style === "quiff") {
    return (
      <group>
        <mesh position={[0, 0.045, -0.01]} scale={[1.04, 0.8, 1.05]} material={mat}><sphereGeometry args={[0.135, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2.1]} /></mesh>
        <mesh position={[0.02, 0.13, 0.07]} rotation={[0.6, 0, -0.2]} scale={[1.3, 0.7, 1]} material={mat}><sphereGeometry args={[0.06, 14, 10]} /></mesh>
      </group>
    );
  }
  if (style === "bun") {
    // centre parting, hair swept over the ears, a low bun at the back
    return (
      <group>
        {[-1, 1].map((sx) => (
          <group key={sx}>
            <mesh position={[sx * 0.045, 0.06, 0]} rotation={[0, 0, sx * -0.5]} scale={[1, 0.62, 1.05]} material={mat}>
              <sphereGeometry args={[0.105, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2]} />
            </mesh>
            <mesh position={[sx * 0.118, -0.005, -0.005]} scale={[0.42, 0.95, 0.95]} material={mat}><sphereGeometry args={[0.085, 14, 10]} /></mesh>
          </group>
        ))}
        <mesh position={[0, 0.03, -0.06]} scale={[1.05, 0.95, 0.75]} material={mat}><sphereGeometry args={[0.13, 20, 14]} /></mesh>
        <mesh position={[0, -0.03, -0.155]} material={mat}><sphereGeometry args={[0.07, 16, 12]} /></mesh>
      </group>
    );
  }
  if (style === "balding") {
    return (
      <group>
        <mesh position={[-0.118, 0.0, -0.02]} scale={[0.45, 0.9, 1.1]} material={mat}><sphereGeometry args={[0.08, 14, 10]} /></mesh>
        <mesh position={[0.118, 0.0, -0.02]} scale={[0.45, 0.9, 1.1]} material={mat}><sphereGeometry args={[0.08, 14, 10]} /></mesh>
        <mesh position={[0, 0.0, -0.1]} scale={[1.3, 0.8, 0.6]} material={mat}><sphereGeometry args={[0.08, 14, 10]} /></mesh>
      </group>
    );
  }
  if (style === "ponytail") {
    return (
      <group>
        <mesh position={[0, 0.04, -0.01]} scale={[1.06, 0.85, 1.06]} material={mat}><sphereGeometry args={[0.135, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2]} /></mesh>
        <mesh position={[0, 0.02, -0.15]} rotation={[0.6, 0, 0]} scale={[0.7, 1.4, 0.7]} material={mat}><sphereGeometry args={[0.06, 14, 10]} /></mesh>
      </group>
    );
  }
  return <mesh position={[0, 0.04, -0.01]} scale={[1.04, 0.78, 1.04]} material={mat}><sphereGeometry args={[0.135, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2.1]} /></mesh>;
}

// ── objects & concepts ────────────────────────────────────────────────────

function Device(props: FigureProps) {
  const { character, position, dimmed, lookAt, reaction, seed = 0, plate } = props;
  const p = palette(character.visual?.palette);
  const glyph = character.visual?.glyph ?? "";
  const shape = shapeFor(character.name, glyph);
  const { expression, tick } = useLife(props);
  const face = FACE[expression];
  const root = useRef<THREE.Group>(null);
  const body = useRef<THREE.Group>(null);
  const mouth = useRef<THREE.Mesh>(null);
  const eyes = useRef<THREE.Group>(null);
  const browL = useRef<THREE.Mesh>(null);
  const browR = useRef<THREE.Mesh>(null);
  const armL = useRef<THREE.Group>(null);
  const armR = useRef<THREE.Group>(null);
  const mats = useMemo(() => ({
    body: new THREE.MeshStandardMaterial({ color: p.base, roughness: 0.45, metalness: 0.15 }),
    dark: new THREE.MeshStandardMaterial({ color: p.dark, roughness: 0.5 }),
    screen: new THREE.MeshStandardMaterial({ color: "#0c0c0d", roughness: 0.15, metalness: 0.4 }),
    glow: new THREE.MeshBasicMaterial({ color: "#f5f0e6", toneMapped: false }),
    limb: new THREE.MeshStandardMaterial({ color: "#1d1b19", roughness: 0.6 }),
  }), [p.base, p.dark]);
  const label = useMemo(() => (glyph && !/\p{Extended_Pictographic}/u.test(glyph)
    ? labelTexture(glyph, { w: 256, h: 128, font: "700 72px ui-monospace, monospace", color: p.light, bg: "rgba(0,0,0,0)", border: "rgba(0,0,0,0)" })
    : null), [glyph, p.light]);
  const plateTex = useMemo(() => (plate ? labelTexture(plate, { w: 640, h: 110 }) : null), [plate]);

  // body proportions per shape (width, height, depth) and where the face sits
  const dims: Record<string, [number, number, number]> = {
    block: [0.62, 0.78, 0.42], monitor: [0.8, 0.58, 0.12], rack: [0.6, 1.0, 0.5], calendar: [0.62, 0.74, 0.12],
    router: [0.8, 0.5, 0.36], clock: [0.7, 0.7, 0.22], battery: [0.5, 0.86, 0.36], mug: [0.6, 0.66, 0.6],
    printer: [0.8, 0.56, 0.6], orb: [0.7, 0.7, 0.7], bubble: [0.8, 0.62, 0.2],
  };
  const [w, h, d] = dims[shape] ?? dims.block;
  const legH = 0.42;
  const cy = legH + h / 2;
  const faceY = cy + (shape === "calendar" ? -0.06 : 0.04);

  useFrame(({ clock }, dt) => {
    const t = clock.elapsedTime + seed * 1.1;
    const { open, blink } = tick(clock.elapsedTime);
    if (!root.current || !body.current) return;
    let yaw = props.speaking ? Math.sin(t * 0.8) * 0.15 : 0;
    if (!props.speaking && lookAt) yaw = THREE.MathUtils.clamp(Math.atan2(lookAt[0] - position[0], lookAt[2] - position[2]) * 0.6, -0.7, 0.7);
    damp(body.current, "y", yaw, dt, 3);
    const hop = reaction === "gasp" || reaction === "shocked" ? Math.max(0, Math.sin(t * 10)) * 0.08 : 0;
    body.current.position.y = Math.sin(t * 1.8) * 0.012 + open * 0.035 + hop;
    damp(body.current, "z", Math.sin(t * 1.1) * 0.025 + (props.speaking ? Math.sin(t * 5) * open * 0.05 : 0), dt, 5);
    if (mouth.current) {
      const ry = props.speaking ? 0.012 + open * 0.06 : 0.008 + Math.max(0, face.smile) * 0.01;
      mouth.current.scale.set(0.05 + (props.speaking ? open * 0.01 : Math.abs(face.smile) * 0.02), ry, 1);
    }
    if (eyes.current) eyes.current.scale.y = Math.max(0.08, Math.min(1.35, face.eye) * (1 - blink));
    if (browL.current && browR.current) {
      browL.current.rotation.z = -face.brow[0] * 0.7;
      browR.current.rotation.z = face.brow[0] * 0.7;
    }
    if (armR.current) damp(armR.current, "z", props.speaking ? 0.9 + Math.sin(t * 3) * 0.4 * (0.4 + open) : 0.25, dt, 5);
    if (armL.current) damp(armL.current, "z", props.speaking && open > 0.4 ? -0.8 : -0.25, dt, 5);
    mats.body.color.lerp(new THREE.Color(p.base).multiplyScalar(dimmed ? 0.55 : 1), Math.min(1, dt * 4));
  });

  return (
    <group ref={root} position={position} scale={FIGURE_SCALE}>
      <group ref={body}>
        {/* legs + shoes */}
        {[-1, 1].map((sx) => (
          <group key={sx} position={[sx * w * 0.22, 0, 0]}>
            <mesh position={[0, legH / 2, 0]} material={mats.limb} castShadow><cylinderGeometry args={[0.03, 0.03, legH, 10]} /></mesh>
            <mesh position={[0, 0.03, 0.04]} scale={[1, 0.6, 1.6]} material={mats.limb}><sphereGeometry args={[0.055, 12, 10]} /></mesh>
          </group>
        ))}
        {/* arms */}
        <group ref={armL} position={[-w / 2, cy, 0]}>
          <mesh position={[-0.12, 0, 0]} rotation={[0, 0, Math.PI / 2]} material={mats.limb}><cylinderGeometry args={[0.022, 0.022, 0.24, 8]} /></mesh>
          <mesh position={[-0.25, 0, 0]} material={mats.limb}><sphereGeometry args={[0.045, 10, 8]} /></mesh>
        </group>
        <group ref={armR} position={[w / 2, cy, 0]}>
          <mesh position={[0.12, 0, 0]} rotation={[0, 0, Math.PI / 2]} material={mats.limb}><cylinderGeometry args={[0.022, 0.022, 0.24, 8]} /></mesh>
          <mesh position={[0.25, 0, 0]} material={mats.limb}><sphereGeometry args={[0.045, 10, 8]} /></mesh>
        </group>
        <DeviceBody shape={shape} w={w} h={h} d={d} cy={cy} mats={mats} />
        {/* the screen-face */}
        <group position={[0, faceY, (shape === "orb" ? w / 2 : d / 2) + 0.006]}>
          {shape !== "orb" && shape !== "clock" && (
            <mesh material={mats.screen}><planeGeometry args={[w * 0.74, h * 0.5]} /></mesh>
          )}
          <group ref={eyes} position={[0, 0.04, 0.004]}>
            {[-1, 1].map((sx) => (
              <mesh key={sx} position={[sx * w * 0.14, 0, 0]} material={mats.glow}><circleGeometry args={[0.032, 18]} /></mesh>
            ))}
          </group>
          <mesh ref={browL} position={[-w * 0.14, 0.1, 0.004]} material={mats.glow}><planeGeometry args={[0.07, 0.012]} /></mesh>
          <mesh ref={browR} position={[w * 0.14, 0.1, 0.004]} material={mats.glow}><planeGeometry args={[0.07, 0.012]} /></mesh>
          <mesh ref={mouth} position={[0, -0.07, 0.004]} scale={[0.05, 0.01, 1]} material={mats.glow}><circleGeometry args={[1, 24]} /></mesh>
        </group>
        {label && (
          <mesh position={[0, legH + h * 0.16, (shape === "orb" ? w / 2 : d / 2) + 0.007]}>
            <planeGeometry args={[w * 0.5, w * 0.25]} />
            <meshBasicMaterial map={label} transparent toneMapped={false} />
          </mesh>
        )}
      </group>
      {plateTex && (
        <mesh position={[0, 0.04, 0.6]}>
          <planeGeometry args={[0.9, 0.9 * (110 / 640)]} />
          <meshStandardMaterial map={plateTex} metalness={0.3} roughness={0.5} />
        </mesh>
      )}
      <ReactionChip reaction={reaction} y={legH + h + 0.25} />
    </group>
  );
}

function DeviceBody({ shape, w, h, d, cy, mats }: { shape: string; w: number; h: number; d: number; cy: number; mats: { body: THREE.Material; dark: THREE.Material; limb: THREE.Material } }) {
  switch (shape) {
    case "orb":
      return <mesh position={[0, cy, 0]} material={mats.body} castShadow><sphereGeometry args={[w / 2, 32, 24]} /></mesh>;
    case "clock":
      return (
        <group>
          <mesh position={[0, cy, 0]} rotation={[Math.PI / 2, 0, 0]} material={mats.body} castShadow><cylinderGeometry args={[w / 2, w / 2, d, 40]} /></mesh>
          {[-1, 1].map((sx) => (
            <mesh key={sx} position={[sx * w * 0.32, cy + h * 0.48, 0]} material={mats.dark}><sphereGeometry args={[0.1, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} /></mesh>
          ))}
        </group>
      );
    case "mug":
      return (
        <group>
          <mesh position={[0, cy, 0]} material={mats.body} castShadow><cylinderGeometry args={[w / 2, w / 2.3, h, 32]} /></mesh>
          <mesh position={[w / 2 + 0.06, cy, 0]} rotation={[0, 0, 0]} material={mats.body}><torusGeometry args={[0.13, 0.035, 10, 24]} /></mesh>
        </group>
      );
    case "router":
      return (
        <group>
          <RoundedBox args={[w, h, d]} radius={0.06} position={[0, cy, 0]} material={mats.body} castShadow />
          {[-1, 1].map((sx) => (
            <mesh key={sx} position={[sx * w * 0.36, cy + h / 2 + 0.22, -d * 0.2]} rotation={[0, 0, sx * -0.25]} material={mats.dark}><cylinderGeometry args={[0.022, 0.022, 0.5, 8]} /></mesh>
          ))}
        </group>
      );
    case "rack":
      return (
        <group>
          <RoundedBox args={[w, h, d]} radius={0.03} position={[0, cy, 0]} material={mats.body} castShadow />
          {[0.3, 0.42].map((f) => (
            <mesh key={f} position={[0, cy - h / 2 + h * f * 0.5, d / 2 + 0.003]} material={mats.dark}><planeGeometry args={[w * 0.8, 0.05]} /></mesh>
          ))}
        </group>
      );
    case "battery":
      return (
        <group>
          <RoundedBox args={[w, h, d]} radius={0.08} position={[0, cy, 0]} material={mats.body} castShadow />
          <mesh position={[0, cy + h / 2 + 0.04, 0]} material={mats.dark}><cylinderGeometry args={[0.08, 0.08, 0.08, 16]} /></mesh>
        </group>
      );
    case "calendar":
      return (
        <group>
          <RoundedBox args={[w, h, d]} radius={0.04} position={[0, cy, 0]} material={new THREE.MeshStandardMaterial({ color: "#efe8da", roughness: 0.8 })} castShadow />
          <RoundedBox args={[w + 0.01, h * 0.22, d + 0.01]} radius={0.04} position={[0, cy + h * 0.39, 0]} material={mats.body} />
          {[-1, 0, 1].map((sx) => (
            <mesh key={sx} position={[sx * w * 0.3, cy + h / 2 + 0.03, 0]} rotation={[Math.PI / 2, 0, 0]} material={mats.dark}><torusGeometry args={[0.03, 0.01, 6, 14]} /></mesh>
          ))}
        </group>
      );
    case "monitor":
      return (
        <group>
          <RoundedBox args={[w, h, d]} radius={0.03} position={[0, cy + 0.12, 0]} material={mats.body} castShadow />
          <mesh position={[0, cy - h / 2 + 0.02, 0]} material={mats.dark}><cylinderGeometry args={[0.05, 0.08, 0.2, 12]} /></mesh>
        </group>
      );
    default:
      return <RoundedBox args={[w, h, d]} radius={0.08} smoothness={4} position={[0, cy, 0]} material={mats.body} castShadow />;
  }
}
