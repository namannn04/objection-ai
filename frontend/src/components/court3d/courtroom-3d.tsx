"use client";

import { AdaptiveDpr, Environment, Lightformer, PerformanceMonitor, Sparkles } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer, N8AO, Noise, Vignette } from "@react-three/postprocessing";
import { easing } from "maath";
import { Suspense, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { CharacterPortrait } from "@/components/characters/character-portrait";
import type { AmplitudeSource } from "@/components/characters/face-parts";
import type { CharacterInfo, Reaction } from "@/lib/types";
import { cn } from "@/lib/utils";
import { PaperRain } from "./paper-rain";
import { CourtroomSet } from "./set";
import { Standee } from "./standee";

type Seat = "judge" | "witness" | "defendant" | "prosecutor" | "defense";
type V3 = [number, number, number];

const SEATS: Record<Seat, { pos: V3; h: number; rotY: number }> = {
  judge: { pos: [0, 1.25, -5.15], h: 2.7, rotY: 0 },
  witness: { pos: [4.2, 0.72, -3.95], h: 2.3, rotY: -0.25 },
  defendant: { pos: [0, 0.32, 0.55], h: 2.35, rotY: 0 },
  prosecutor: { pos: [-3.7, 0.42, 1.55], h: 2.6, rotY: 0.22 },
  defense: { pos: [3.7, 0.42, 1.55], h: 2.6, rotY: -0.22 },
};

interface Shot { pos: V3; look: V3; fov: number }

// The camera director's shot list. Each speaker gets a composed medium shot.
const SHOTS: Record<Seat | "wide" | "verdict" | "objection", Shot> = {
  wide: { pos: [0, 3.2, 10.2], look: [0, 2.0, -2.2], fov: 46 },
  judge: { pos: [0, 3.0, 1.2], look: [0, 2.5, -5.1], fov: 42 },
  witness: { pos: [2.7, 2.35, 2.0], look: [4.2, 1.7, -3.9], fov: 40 },
  defendant: { pos: [0, 1.75, 5.9], look: [0, 1.25, 0.5], fov: 40 },
  prosecutor: { pos: [-2.6, 1.95, 6.8], look: [-3.7, 1.55, 1.55], fov: 40 },
  defense: { pos: [2.6, 1.95, 6.8], look: [3.7, 1.55, 1.55], fov: 40 },
  verdict: { pos: [0, 3.75, -1.7], look: [0, 3.0, -5.1], fov: 34 },
  objection: { pos: [0, 2.3, 6.6], look: [0, 1.8, -1], fov: 52 },
};

function seatOf(c: CharacterInfo, witnessKey: string | null): Seat | null {
  if (c.role === "witness") return c.key === witnessKey ? "witness" : null;
  if (c.role === "reporter") return null;
  return c.role as Seat;
}

export interface Courtroom3DProps {
  characters: CharacterInfo[];
  speaker?: string | null;
  emotion?: string;
  reactions?: Record<string, Reaction>;
  amplitude?: AmplitudeSource | null;
  witnessKey?: string | null;
  burst?: number;
  gavel?: number;
  celebrate?: boolean;
  verdict?: boolean;
  segmentKind?: string;
  caseNumber?: string;
  className?: string;
  children?: React.ReactNode;
  live?: boolean;
  /** Decorative mode for the landing page: slow orbit, lighter effects. */
  showcase?: boolean;
}

function Director({ speakerSeat, burst, verdict, showcase }: { speakerSeat: Seat | null; burst: number; verdict: boolean; showcase: boolean }) {
  const look = useRef(new THREE.Vector3(...SHOTS.wide.look));
  const lastBurst = useRef(burst);
  const shake = useRef(0);
  const whip = useRef(0);
  useFrame(({ clock, camera }, dt) => {
    if (burst !== lastBurst.current) {
      lastBurst.current = burst;
      shake.current = 1;
      whip.current = 1;
    }
    const t = clock.elapsedTime;
    let shot = verdict ? SHOTS.verdict : speakerSeat ? SHOTS[speakerSeat] : SHOTS.wide;
    if (whip.current > 0.35) shot = SHOTS.objection;
    if (showcase) {
      const a = Math.sin(t * 0.12) * 0.55;
      shot = { pos: [Math.sin(a) * 12.4, 3.6 + Math.sin(t * 0.2) * 0.3, Math.cos(a) * 12.4], look: [0, 1.9, -2.6], fov: 40 };
    }
    const speed = whip.current > 0.35 ? 0.12 : verdict ? 1.6 : 0.85;
    easing.damp3(camera.position, shot.pos, speed, dt);
    easing.damp3(look.current, shot.look, speed * 0.9, dt);
    const cam = camera as THREE.PerspectiveCamera;
    cam.fov = THREE.MathUtils.damp(cam.fov, shot.fov, 3, dt);
    cam.updateProjectionMatrix();
    // handheld drift + objection shake
    const drift = showcase ? 0 : 0.02;
    const s = shake.current * 0.09;
    camera.lookAt(
      look.current.x + Math.sin(t * 0.7) * drift + (Math.random() - 0.5) * s,
      look.current.y + Math.sin(t * 0.9) * drift + (Math.random() - 0.5) * s,
      look.current.z,
    );
    shake.current = Math.max(0, shake.current - dt * 2.2);
    whip.current = Math.max(0, whip.current - dt * 1.4);
  });
  return null;
}

/** One shadow-casting key light that glides to whoever is talking; soft fills everywhere else. */
function Lighting({ speakerSeat }: { speakerSeat: Seat | null }) {
  const key = useRef<THREE.SpotLight>(null);
  const target = useMemo(() => new THREE.Object3D(), []);
  const benchTarget = useMemo(() => {
    const o = new THREE.Object3D();
    o.position.set(0, 2.2, -5.2);
    return o;
  }, []);
  useFrame((_, dt) => {
    const seat = speakerSeat ? SEATS[speakerSeat] : null;
    const goal: V3 = seat ? [seat.pos[0], seat.pos[1] + seat.h * 0.6, seat.pos[2]] : [0, 1.6, -1.5];
    easing.damp3(target.position, goal, 0.45, dt);
    if (key.current) {
      easing.damp3(key.current.position, [goal[0] * 0.6, 7.2, goal[2] + 5], 0.6, dt);
      key.current.intensity = THREE.MathUtils.damp(key.current.intensity, speakerSeat === "judge" ? 45 : seat ? 75 : 55, 4, dt);
      key.current.target = target;
    }
  });
  return (
    <>
      <primitive object={target} />
      <primitive object={benchTarget} />
      <ambientLight intensity={0.42} color="#ffe6c4" />
      <hemisphereLight args={["#5a4430", "#080606", 0.75]} />
      <spotLight
        ref={key}
        position={[0, 7.2, 4]}
        angle={0.32}
        penumbra={0.7}
        intensity={80}
        distance={22}
        decay={1.5}
        color="#ffe9c7"
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0004}
      />
      {/* the bench always gets a little holy light */}
      <spotLight position={[0, 6.8, -1.2]} angle={0.42} penumbra={0.9} intensity={9} distance={12} color="#ffd9a0" target={benchTarget} />
      <directionalLight position={[8, 6, -2]} intensity={0.55} color="#c9d4ff" />
    </>
  );
}

function Scene({ characters, speaker, emotion, reactions = {}, amplitude = null, witnessKey, burst = 0, gavel = 0, celebrate = false, verdict = false, showcase = false, reflections }: Courtroom3DProps & { reflections: boolean }) {
  const witness = witnessKey ?? characters.find((c) => c.role === "witness" && !c.surprise)?.key ?? null;
  const placed = characters
    .map((c) => ({ c, seat: seatOf(c, witness) }))
    .filter((p): p is { c: CharacterInfo; seat: Seat } => p.seat !== null);
  const active = placed.find((p) => p.c.key === speaker)?.seat ?? null;
  return (
    <>
      <color attach="background" args={["#070606"]} />
      <fog attach="fog" args={["#070606", 14, 32]} />
      <Lighting speakerSeat={active} />
      <Director speakerSeat={active} burst={burst} verdict={verdict} showcase={showcase} />
      <CourtroomSet reflections={reflections} gavel={gavel} />
      <PaperRain active={celebrate} />
      {placed.map(({ c, seat }, i) => {
        const s = SEATS[seat];
        return (
          <Standee
            key={c.key}
            character={c}
            position={s.pos}
            height={s.h}
            rotationY={s.rotY}
            speaking={speaker === c.key}
            emotion={speaker === c.key ? emotion : undefined}
            reaction={reactions[c.key] ?? null}
            dimmed={!!speaker && speaker !== c.key && !!active}
            amplitude={speaker === c.key ? amplitude : null}
            base={seat === "defendant"}
            plate={seat === "defendant" ? "The Defendant" : undefined}
            seed={i}
          />
        );
      })}
      {/* local studio environment (no network): warm softboxes for believable reflections on wood and brass */}
      <Environment resolution={128} frames={1} environmentIntensity={0.35}>
        <Lightformer form="rect" intensity={2.2} color="#ffd9a8" position={[0, 6, 2]} rotation-x={Math.PI / 2} scale={[10, 4, 1]} />
        <Lightformer form="rect" intensity={1.2} color="#c9d4ff" position={[9, 3, -2]} rotation-y={-Math.PI / 2} scale={[6, 3, 1]} />
        <Lightformer form="ring" intensity={1.5} color="#ffcf8a" position={[0, 4, -7]} scale={3} />
      </Environment>
      <Sparkles count={70} scale={[14, 6, 12]} position={[0, 3.2, -1]} size={1.6} speed={0.18} opacity={0.35} color="#ffe2b0" />
      <EffectComposer multisampling={0} enableNormalPass={false}>
        {reflections ? <N8AO aoRadius={0.6} intensity={2.2} distanceFalloff={0.8} halfRes quality="low" /> : <></>}
        <Bloom intensity={0.42} luminanceThreshold={0.82} luminanceSmoothing={0.2} mipmapBlur />
        <Vignette eskil={false} offset={0.22} darkness={0.82} />
        <Noise opacity={0.045} />
      </EffectComposer>
    </>
  );
}

export default function Courtroom3D(props: Courtroom3DProps) {
  const { characters, speaker, amplitude = null, caseNumber, className, children, live = true, showcase = false } = props;
  const [reflections, setReflections] = useState(true);
  const reporter = characters.find((c) => c.role === "reporter");
  return (
    <div className={cn("relative aspect-[16/9] w-full overflow-hidden rounded-[18px] border hairline bg-[#070606]", className)}>
      <Canvas
        shadows
        dpr={[1, showcase ? 1.25 : 1.6]}
        gl={{ antialias: false, powerPreference: "high-performance", toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}
        camera={{ position: SHOTS.wide.pos, fov: SHOTS.wide.fov, near: 0.1, far: 60 }}
        aria-label="3D courtroom"
      >
        <PerformanceMonitor onDecline={() => setReflections(false)} />
        <AdaptiveDpr pixelated={false} />
        <Suspense fallback={null}>
          <Scene {...props} reflections={reflections} />
        </Suspense>
      </Canvas>
      {reporter && !showcase && (
        <div className="pointer-events-none absolute left-[2.5%] top-[4%] z-[7] w-[8.5%] min-w-[54px]">
          <div className={cn("aspect-square overflow-hidden rounded-full border bg-ink-3 transition-colors duration-500", speaker === reporter.key ? "border-gold" : "border-line-strong")}>
            <div className="h-[118%] w-full translate-y-[2%]">
              <CharacterPortrait character={reporter} speaking={speaker === reporter.key} amplitude={speaker === reporter.key ? amplitude : null} className="h-full w-full" />
            </div>
          </div>
          <div className="mt-1.5 flex items-center justify-center gap-1 whitespace-nowrap font-mono text-[7px] tracking-[0.2em] text-mute sm:text-[9px]">
            <span className={cn("h-1.5 w-1.5 rounded-full", live ? "animate-blink bg-burgundy-bright" : "bg-mute")} />ON AIR
          </div>
        </div>
      )}
      {caseNumber && (
        <div className="pointer-events-none absolute right-[2.5%] top-[4%] z-[9] font-mono text-[9px] tracking-[0.2em] text-mute sm:text-[10px]">{caseNumber}</div>
      )}
      <div className="absolute inset-0 z-[10]">{children}</div>
    </div>
  );
}
