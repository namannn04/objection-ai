"use client";

import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { AmplitudeSource } from "@/components/characters/face-parts";
import { REACTION_TO_EXPRESSION, expressionFor, type Expression } from "@/components/characters/palette";
import type { CharacterInfo, Reaction } from "@/lib/types";
import { labelTexture, mouthAnchor, portraitTexture, radialTexture } from "./textures";

const MARK: Partial<Record<Reaction, string>> = {
  gasp: "!", shocked: "!!", confused: "?", laugh: "ha", angry: "#", sweat: "…", facepalm: "ugh", smirk: "heh", nod: "mm",
};

export interface StandeeProps {
  character: CharacterInfo;
  position: [number, number, number];
  height: number;
  rotationY?: number;
  speaking: boolean;
  emotion?: string;
  reaction?: Reaction | null;
  dimmed: boolean;
  amplitude: AmplitudeSource | null;
  base?: boolean;
  seed?: number;
  plate?: string;
}

const shadowTex = typeof document !== "undefined" ? radialTexture() : null;

/** A paper-theatre cut-out: the character's illustration on a card, lit by the room, casting a real shadow. */
export function Standee({ character, position, height, rotationY = 0, speaking, emotion, reaction, dimmed, amplitude, base = true, seed = 0, plate }: StandeeProps) {
  const width = height / 1.1;
  const expression: Expression = reaction ? REACTION_TO_EXPRESSION[reaction] : speaking ? expressionFor(emotion) : "neutral";
  const [tex, setTex] = useState<THREE.Texture | null>(null);
  const group = useRef<THREE.Group>(null);
  const card = useRef<THREE.Mesh>(null);
  const mouth = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshStandardMaterial>(null);
  const smooth = useRef(0);
  const anchor = mouthAnchor(character);
  const plateTex = useMemo(() => (plate ? labelTexture(plate, { w: 640, h: 110 }) : null), [plate]);

  useEffect(() => {
    let alive = true;
    portraitTexture(character, expression, !speaking).then((t) => alive && setTex(t), () => undefined);
    return () => {
      alive = false;
    };
  }, [character, expression, speaking]);

  const depthMat = useMemo(() => {
    const m = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, alphaTest: 0.5 });
    m.map = tex;
    return m;
  }, [tex]);

  useFrame(({ clock, camera }, dt) => {
    const t = clock.elapsedTime + seed * 1.7;
    const a = speaking && amplitude ? Math.min(1, amplitude() * 5.5) : 0;
    smooth.current += (a - smooth.current) * (a > smooth.current ? 0.55 : 0.22);
    if (group.current) {
      // idle sway; a little bounce while talking; a hop on gasps
      const hop = reaction === "gasp" || reaction === "shocked" ? Math.max(0, Math.sin(t * 9)) * 0.06 : 0;
      group.current.position.y = position[1] + Math.sin(t * 1.3) * 0.012 + smooth.current * 0.05 + hop;
      group.current.rotation.z = Math.sin(t * 0.9) * 0.012 + (reaction === "nod" ? Math.sin(t * 8) * 0.03 : 0);
      // Paper-theatre cut-outs always turn to face the audience (the camera), so they never look razor-thin.
      const face = Math.atan2(camera.position.x - position[0], camera.position.z - position[2]);
      const goal = THREE.MathUtils.clamp(face, -0.9, 0.9) + rotationY * 0 + Math.sin(t * 0.6) * 0.02;
      group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, goal, 4, dt);
    }
    if (mouth.current) {
      const ry = 1.5 + smooth.current * 7.5;
      mouth.current.scale.set(anchor.rx, ry, 1);
      mouth.current.visible = speaking;
    }
    if (mat.current) {
      const target = dimmed ? 0.42 : 1;
      const c = mat.current.color.r + (target - mat.current.color.r) * Math.min(1, dt * 5);
      mat.current.color.setScalar(c);
    }
  });

  // SVG units → card units (viewBox 200×220 maps onto width×height, origin at bottom-centre)
  const toLocal = (x: number, y: number): [number, number] => [(x / 200 - 0.5) * width, (1 - y / 220) * height];
  const [mx, my] = toLocal(anchor.x, anchor.y);
  const unit = width / 200;

  return (
    <group ref={group} position={position}>
      {base && (
        <>
          <mesh position={[0, 0.03, 0.06]} castShadow receiveShadow>
            <boxGeometry args={[width * 0.55, 0.06, 0.32]} />
            <meshStandardMaterial color="#1a120d" roughness={0.5} />
          </mesh>
          <mesh position={[0, 0.062, 0.06]}>
            <boxGeometry args={[width * 0.56, 0.008, 0.33]} />
            <meshStandardMaterial color="#d6ae62" metalness={0.8} roughness={0.3} />
          </mesh>
        </>
      )}
      {plateTex && (
        <mesh position={[0, 0.04, 0.23]}>
          <planeGeometry args={[width * 0.5, width * 0.5 * (110 / 640)]} />
          <meshStandardMaterial map={plateTex} metalness={0.3} roughness={0.5} />
        </mesh>
      )}
      {shadowTex && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0.05]}>
          <planeGeometry args={[width * 0.9, 0.7]} />
          <meshBasicMaterial map={shadowTex} transparent depthWrite={false} opacity={0.7} />
        </mesh>
      )}
      {tex && (
        // die-cut cardboard edge: the same silhouette, a touch larger, in card stock
        <mesh position={[0, height / 2, -0.012]} scale={[1.045, 1.035, 1]}>
          <planeGeometry args={[width, height]} />
          <meshStandardMaterial alphaMap={tex} alphaTest={0.5} color="#d9ccb1" roughness={1} side={THREE.DoubleSide} />
        </mesh>
      )}
      {tex && (
        <mesh ref={card} position={[0, height / 2, 0]} castShadow customDepthMaterial={depthMat}>
          <planeGeometry args={[width, height]} />
          <meshStandardMaterial ref={mat} map={tex} alphaTest={0.5} transparent={false} side={THREE.DoubleSide} roughness={0.85} metalness={0} />
        </mesh>
      )}
      {/* the animated mouth, drawn on top of the card */}
      <mesh ref={mouth} position={[mx, my, 0.004]} scale={[anchor.rx, 1.5, 1]}>
        <circleGeometry args={[unit, 24]} />
        {anchor.glow ? <meshBasicMaterial color={anchor.color} toneMapped={false} /> : <meshBasicMaterial color={anchor.color} />}
      </mesh>
      {reaction && MARK[reaction] && (
        <Html position={[width * 0.32, height * 1.02, 0]} center zIndexRange={[20, 0]}>
          <span className="pointer-events-none select-none rounded-full border border-gold/60 bg-ink/90 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-gold">
            {MARK[reaction]}
          </span>
        </Html>
      )}
    </group>
  );
}
