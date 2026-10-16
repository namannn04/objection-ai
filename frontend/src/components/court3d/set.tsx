"use client";

import { MeshReflectorMaterial } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { carpetTexture, labelTexture, plankTexture, sealTexture, woodTexture } from "./textures";

const GOLD = { color: "#d6ae62", metalness: 0.85, roughness: 0.28 } as const;

function useMats() {
  return useMemo(() => {
    const wood = woodTexture();
    return {
      wood: new THREE.MeshStandardMaterial({ map: wood, roughness: 0.62, metalness: 0.05 }),
      darkWood: new THREE.MeshStandardMaterial({ color: "#1a120d", roughness: 0.55, metalness: 0.08 }),
      gold: new THREE.MeshStandardMaterial(GOLD),
      wall: new THREE.MeshStandardMaterial({ color: "#16110e", roughness: 0.9 }),
      plaster: new THREE.MeshStandardMaterial({ color: "#1f1a16", roughness: 0.95 }),
      juror: new THREE.MeshStandardMaterial({ color: "#0d0b0a", roughness: 0.8 }),
    };
  }, []);
}

type V3 = [number, number, number];

function Box({ args, position, material, rotation, cast = true }: {
  args: V3; position: V3; material: THREE.Material; rotation?: V3; cast?: boolean;
}) {
  return (
    <mesh position={position} rotation={rotation} material={material} castShadow={cast} receiveShadow>
      <boxGeometry args={args} />
    </mesh>
  );
}

/** A paneled front: wood box + gold rail + inset panel lines. */
function Paneled({ w, h, d, position, label, mats }: {
  w: number; h: number; d: number; position: V3; label?: string; mats: ReturnType<typeof useMats>;
}) {
  const plate = useMemo(() => (label ? labelTexture(label, { w: 768, h: 120, font: "600 54px ui-monospace, monospace" }) : null), [label]);
  const [x, y, z] = position;
  const panels = Math.max(2, Math.round(w / 1.1));
  return (
    <group position={[x, y, z]}>
      <Box args={[w, h, d]} position={[0, h / 2, 0]} material={mats.wood} />
      <Box args={[w + 0.12, 0.08, d + 0.14]} position={[0, h + 0.04, 0]} material={mats.gold} />
      <Box args={[w + 0.06, 0.06, d + 0.06]} position={[0, 0.03, 0]} material={mats.gold} cast={false} />
      {Array.from({ length: panels }).map((_, i) => (
        <mesh key={i} position={[-w / 2 + (w / panels) * (i + 0.5), h * 0.45, d / 2 + 0.005]} material={mats.darkWood}>
          <planeGeometry args={[(w / panels) * 0.78, h * 0.62]} />
        </mesh>
      ))}
      {plate && (
        <mesh position={[0, h * 0.72, d / 2 + 0.012]}>
          <planeGeometry args={[Math.min(w * 0.6, 2.2), Math.min(w * 0.6, 2.2) * (120 / 768)]} />
          <meshStandardMaterial map={plate} metalness={0.3} roughness={0.5} />
        </mesh>
      )}
    </group>
  );
}

function Lamp({ position }: { position: V3 }) {
  return (
    <group position={position}>
      <mesh position={[0, 1.2, 0]}>
        <cylinderGeometry args={[0.008, 0.008, 2.4]} />
        <meshBasicMaterial color="#000" />
      </mesh>
      <mesh castShadow={false}>
        <coneGeometry args={[0.45, 0.35, 24, 1, true]} />
        <meshStandardMaterial color="#d6ae62" metalness={0.8} roughness={0.3} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, -0.14, 0]}>
        <sphereGeometry args={[0.11, 16, 16]} />
        <meshBasicMaterial color="#ffe2a8" toneMapped={false} />
      </mesh>
      <pointLight position={[0, -0.3, 0]} intensity={6} distance={7} decay={1.6} color="#ffcf8a" />
    </group>
  );
}

function WallClock({ position }: { position: V3 }) {
  const minute = useRef<THREE.Mesh>(null);
  const hour = useRef<THREE.Mesh>(null);
  // Runs 60× too fast. Time flies when you're in court.
  useFrame((_, dt) => {
    if (minute.current) minute.current.rotation.z -= dt * 0.105 * 6;
    if (hour.current) hour.current.rotation.z -= dt * 0.0087 * 6;
  });
  return (
    <group position={position}>
      <mesh>
        <circleGeometry args={[0.62, 48]} />
        <meshStandardMaterial color="#ece4d2" roughness={0.6} />
      </mesh>
      <mesh position={[0, 0, -0.01]}>
        <circleGeometry args={[0.7, 48]} />
        <meshStandardMaterial {...GOLD} />
      </mesh>
      {Array.from({ length: 12 }).map((_, i) => (
        <mesh key={i} position={[Math.sin((i / 12) * Math.PI * 2) * 0.52, Math.cos((i / 12) * Math.PI * 2) * 0.52, 0.01]}>
          <circleGeometry args={[0.025, 8]} />
          <meshBasicMaterial color="#141414" />
        </mesh>
      ))}
      <mesh ref={hour} position={[0, 0, 0.02]}>
        <planeGeometry args={[0.04, 0.6]} />
        <meshBasicMaterial color="#141414" />
      </mesh>
      <mesh ref={minute} position={[0, 0, 0.03]}>
        <planeGeometry args={[0.025, 0.95]} />
        <meshBasicMaterial color="#6b202a" />
      </mesh>
    </group>
  );
}

/** A tall window at night: moonlit glass, brass frame, mullions. */
function Window({ x, z }: { x: number; z: number }) {
  const dir = Math.sign(x);
  const rot: V3 = [0, -dir * Math.PI / 2, 0];
  return (
    <group position={[x - dir * 0.02, 3.7, z]} rotation={rot}>
      <mesh position={[0, 0, -0.01]}>
        <planeGeometry args={[1.8, 3.6]} />
        <meshStandardMaterial color="#1a1410" roughness={0.6} />
      </mesh>
      <mesh>
        <planeGeometry args={[1.5, 3.3]} />
        <meshBasicMaterial color="#26385c" toneMapped={false} />
      </mesh>
      {/* moon glow in the upper pane */}
      <mesh position={[0.25, 0.95, 0.005]}>
        <circleGeometry args={[0.32, 32]} />
        <meshBasicMaterial color="#5f7db0" transparent opacity={0.55} toneMapped={false} />
      </mesh>
      {[-0.375, 0.375].map((dx) => (
        <mesh key={dx} position={[dx, 0, 0.01]}>
          <planeGeometry args={[0.04, 3.3]} />
          <meshStandardMaterial color="#b8914d" metalness={0.7} roughness={0.35} />
        </mesh>
      ))}
      {[-0.82, 0, 0.82].map((dy) => (
        <mesh key={dy} position={[0, dy, 0.01]}>
          <planeGeometry args={[1.5, 0.04]} />
          <meshStandardMaterial color="#b8914d" metalness={0.7} roughness={0.35} />
        </mesh>
      ))}
      <mesh position={[0, -1.72, 0.06]}>
        <boxGeometry args={[1.9, 0.08, 0.16]} />
        <meshStandardMaterial color="#2a1c14" roughness={0.6} />
      </mesh>
    </group>
  );
}

function JuryBox({ mats }: { mats: ReturnType<typeof useMats> }) {
  const you = useMemo(() => labelTexture("YOU", { w: 256, h: 96, font: "700 52px ui-monospace, monospace" }), []);
  const glow = useRef<THREE.MeshStandardMaterial>(null);
  useFrame(({ clock }) => {
    if (glow.current) glow.current.emissiveIntensity = 0.6 + Math.sin(clock.elapsedTime * 2.2) * 0.35;
  });
  const seats: V3[] = [];
  for (let row = 0; row < 2; row++) for (let i = 0; i < 6; i++) seats.push([-1.5 + i * 0.6, row * 0.45, -row * 0.75]);
  return (
    <group position={[-7.1, 0, -1.6]} rotation={[0, Math.PI / 2.6, 0]}>
      <Box args={[4.4, 0.45, 2.2]} position={[0, 0.22, -0.5]} material={mats.darkWood} />
      <Paneled w={4.2} h={1.05} d={0.15} position={[0, 0, 0.75]} label="The Jury" mats={mats} />
      {seats.map((p, i) => {
        const isYou = i === 3;
        return (
          <group key={i} position={[p[0], 0.45 + p[1], p[2]]}>
            {isYou ? (
              <>
                <mesh position={[0, 0.35, 0]}>
                  <boxGeometry args={[0.42, 0.7, 0.08]} />
                  <meshStandardMaterial ref={glow} color="#3a2a12" emissive="#d6ae62" emissiveIntensity={0.6} />
                </mesh>
                <mesh position={[0, 0.85, 0.06]}>
                  <planeGeometry args={[0.42, 0.16]} />
                  <meshBasicMaterial map={you} toneMapped={false} />
                </mesh>
              </>
            ) : (
              <>
                {/* shoulders, neck, head: a proper silhouette, not a bowling pin */}
                <mesh position={[0, 0.42, 0]} scale={[1, 1, 0.62]} material={mats.juror} castShadow>
                  <sphereGeometry args={[0.24, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
                </mesh>
                <mesh position={[0, 0.26, 0]} scale={[1, 1, 0.62]} material={mats.juror}>
                  <cylinderGeometry args={[0.24, 0.26, 0.32, 16]} />
                </mesh>
                <mesh position={[0, 0.72, 0]} scale={[0.9 + (i % 3) * 0.06, 1.05 + (i % 4) * 0.04, 0.95]} material={mats.juror} castShadow>
                  <sphereGeometry args={[0.13, 16, 14]} />
                </mesh>
              </>
            )}
          </group>
        );
      })}
    </group>
  );
}

/** The gavel lifts and slams on every strike. */
function Gavel({ strikes }: { strikes: number }) {
  const arm = useRef<THREE.Group>(null);
  const last = useRef(strikes);
  const t = useRef(1);
  useFrame((_, dt) => {
    if (strikes !== last.current) {
      last.current = strikes;
      t.current = 0;
    }
    t.current = Math.min(1, t.current + dt * 2.4);
    // 0→0.35 wind up, 0.35→0.5 slam, then settle
    const p = t.current;
    const angle = p < 0.35 ? (p / 0.35) * 0.9 : p < 0.5 ? 0.9 - ((p - 0.35) / 0.15) * 0.95 : -0.05 * (1 - p);
    if (arm.current) arm.current.rotation.z = angle;
  });
  return (
    <group position={[2.15, 2.14, -4.6]} rotation={[0, 0.4, 0]}>
      <mesh position={[0, -0.005, 0]} receiveShadow>
        <cylinderGeometry args={[0.16, 0.18, 0.04, 24]} />
        <meshStandardMaterial color="#2a1a10" roughness={0.4} />
      </mesh>
      <group ref={arm} position={[0.42, 0.05, 0]}>
        <mesh position={[-0.2, 0, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.022, 0.026, 0.42, 10]} />
          <meshStandardMaterial color="#3a2414" roughness={0.4} />
        </mesh>
        <mesh position={[-0.42, 0.02, 0]} castShadow>
          <cylinderGeometry args={[0.07, 0.07, 0.24, 18]} />
          <meshStandardMaterial color="#3a2414" roughness={0.35} />
        </mesh>
        <mesh position={[-0.42, 0.02, 0]}>
          <cylinderGeometry args={[0.072, 0.072, 0.03, 18]} />
          <meshStandardMaterial color="#d6ae62" metalness={0.85} roughness={0.3} />
        </mesh>
      </group>
    </group>
  );
}

function Sconce({ position }: { position: V3 }) {
  return (
    <group position={position}>
      <mesh position={[0, -0.1, 0.06]}>
        <boxGeometry args={[0.12, 0.42, 0.06]} />
        <meshStandardMaterial {...GOLD} />
      </mesh>
      <mesh position={[0, 0.2, 0.16]}>
        <cylinderGeometry args={[0.13, 0.09, 0.26, 18, 1, true]} />
        <meshStandardMaterial color="#f3dfb6" emissive="#ffcf8a" emissiveIntensity={1.4} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      <pointLight position={[0, 0.25, 0.4]} intensity={3.2} distance={5} decay={1.7} color="#ffc977" />
    </group>
  );
}

/** A fictional court banner on a pole: burgundy, gold seal, swaying a little. */
function Banner({ position, phase = 0 }: { position: V3; phase?: number }) {
  const cloth = useRef<THREE.Mesh>(null);
  const seal = useMemo(() => sealTexture(), []);
  useFrame(({ clock }) => {
    if (cloth.current) cloth.current.rotation.y = Math.sin(clock.elapsedTime * 0.8 + phase) * 0.12;
  });
  return (
    <group position={position}>
      <mesh position={[0, 2.4, 0]} castShadow>
        <cylinderGeometry args={[0.035, 0.045, 4.8, 10]} />
        <meshStandardMaterial {...GOLD} />
      </mesh>
      <mesh position={[0, 4.9, 0]}>
        <sphereGeometry args={[0.09, 14, 14]} />
        <meshStandardMaterial {...GOLD} />
      </mesh>
      <mesh ref={cloth} position={[0.55, 3.55, 0]} castShadow>
        <planeGeometry args={[1.05, 2.1]} />
        <meshStandardMaterial color="#6b202a" roughness={0.9} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0.55, 3.75, 0.012]}>
        <circleGeometry args={[0.36, 40]} />
        <meshStandardMaterial map={seal} transparent emissive="#d6ae62" emissiveMap={seal} emissiveIntensity={0.35} />
      </mesh>
      <Box args={[1.07, 0.08, 0.04]} position={[0.55, 4.62, 0]} material={new THREE.MeshStandardMaterial(GOLD)} cast={false} />
    </group>
  );
}

/** Gallery pews behind the bar — depth in the foreground of the wide shot. */
function GalleryBenches({ mats }: { mats: ReturnType<typeof useMats> }) {
  const rows = [5.6, 6.9, 8.2];
  return (
    <group>
      {rows.flatMap((z) =>
        [-1, 1].map((side) => (
          <group key={`${z}${side}`} position={[side * 4.9, 0, z]}>
            <Box args={[6.2, 0.08, 0.55]} position={[0, 0.48, 0]} material={mats.wood} />
            <Box args={[6.2, 0.62, 0.07]} position={[0, 0.85, 0.27]} material={mats.wood} />
            <Box args={[6.25, 0.05, 0.1]} position={[0, 1.17, 0.27]} material={mats.gold} cast={false} />
            {[-3, 3].map((x) => (
              <Box key={x} args={[0.08, 0.95, 0.6]} position={[x, 0.48, 0.02]} material={mats.darkWood} />
            ))}
          </group>
        )),
      )}
    </group>
  );
}

export function CourtroomSet({ reflections = true, gavel = 0, judgeName = "Hon. Judge" }: { reflections?: boolean; gavel?: number; judgeName?: string }) {
  const mats = useMats();
  const planks = useMemo(() => plankTexture(), []);
  const carpet = useMemo(() => carpetTexture(), []);
  const seal = useMemo(() => sealTexture(), []);
  const motto = useMemo(() => labelTexture("In Nonsense We Trust", { w: 1400, h: 120, font: "italic 600 70px Georgia, serif", bg: "rgba(0,0,0,0)", border: "rgba(0,0,0,0)" }), []);
  const balusters = useMemo(() => Array.from({ length: 26 }, (_, i) => -7.5 + i * 0.6).filter((x) => Math.abs(x) > 0.7), []);

  return (
    <group>
      {/* floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[19, 18]} />
        {reflections ? (
          <MeshReflectorMaterial map={planks} mirror={0.22} blur={[320, 90]} resolution={512} mixBlur={1} mixStrength={1.1}
            roughness={0.62} depthScale={0.7} minDepthThreshold={0.4} maxDepthThreshold={1.2} color="#ffffff" metalness={0.15} />
        ) : (
          <meshStandardMaterial map={planks} roughness={0.45} metalness={0.1} />
        )}
      </mesh>
      {/* carpet runner down the aisle to the dock */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.006, 5.2]} receiveShadow>
        <planeGeometry args={[2.1, 9.4]} />
        <meshStandardMaterial map={carpet} roughness={1} />
      </mesh>

      {/* ceiling: coffered, with recessed lights */}
      <mesh position={[0, 7.4, 0.5]} rotation={[Math.PI / 2, 0, 0]} material={mats.plaster}>
        <planeGeometry args={[19, 18]} />
      </mesh>
      {[-6, -2, 2, 6].map((x) => (
        <Box key={`bx${x}`} args={[0.35, 0.3, 18]} position={[x, 7.25, 0.5]} material={mats.darkWood} cast={false} />
      ))}
      {[-5, -1, 3, 7].map((z) => (
        <Box key={`bz${z}`} args={[19, 0.3, 0.35]} position={[0, 7.25, z]} material={mats.darkWood} cast={false} />
      ))}
      {[[-4, -3], [0, -3], [4, -3], [-4, 1], [4, 1], [-4, 5], [0, 5], [4, 5]].map(([x, z]) => (
        <mesh key={`rl${x}${z}`} position={[x, 7.38, z]} rotation={[Math.PI / 2, 0, 0]}>
          <circleGeometry args={[0.16, 20]} />
          <meshBasicMaterial color="#ffe6b8" toneMapped={false} />
        </mesh>
      ))}
      {/* crown molding */}
      <Box args={[19, 0.22, 0.3]} position={[0, 7.1, -7.32]} material={mats.gold} cast={false} />
      <Box args={[0.3, 0.22, 18]} position={[-9.33, 7.1, 0.5]} material={mats.gold} cast={false} />
      <Box args={[0.3, 0.22, 18]} position={[9.33, 7.1, 0.5]} material={mats.gold} cast={false} />

      <Sconce position={[-3.4, 3.6, -7.28]} />
      <Sconce position={[3.4, 3.6, -7.28]} />
      <Banner position={[-4.6, 0, -6.6]} />
      <Banner position={[4.6, 0, -6.6]} phase={1.3} />
      <GalleryBenches mats={mats} />

      {/* walls */}
      <mesh position={[0, 4, -7.5]} material={mats.wall} receiveShadow><planeGeometry args={[19, 8]} /></mesh>
      <mesh position={[-9.5, 4, 0.5]} rotation={[0, Math.PI / 2, 0]} material={mats.wall} receiveShadow><planeGeometry args={[18, 8]} /></mesh>
      <mesh position={[9.5, 4, 0.5]} rotation={[0, -Math.PI / 2, 0]} material={mats.wall} receiveShadow><planeGeometry args={[18, 8]} /></mesh>
      {/* wainscoting along back wall */}
      <Box args={[19, 2.2, 0.12]} position={[0, 1.1, -7.42]} material={mats.wood} cast={false} />
      <Box args={[19, 0.07, 0.18]} position={[0, 2.22, -7.4]} material={mats.gold} cast={false} />
      {Array.from({ length: 9 }).map((_, i) => (
        <Box key={i} args={[0.22, 5.6, 0.25]} position={[-8.4 + i * 2.1, 2.8, -7.35]} material={mats.darkWood} cast={false} />
      ))}

      {/* seal + motto behind the bench */}
      <mesh position={[0, 4.55, -7.3]}>
        <circleGeometry args={[2.05, 64]} />
        <meshStandardMaterial map={seal} transparent emissive="#d6ae62" emissiveMap={seal} emissiveIntensity={0.55} metalness={0.6} roughness={0.35} />
      </mesh>
      <mesh position={[0, 6.95, -7.3]}>
        <planeGeometry args={[5.6, 0.48]} />
        <meshBasicMaterial map={motto} transparent toneMapped={false} />
      </mesh>
      <WallClock position={[-5.6, 4.6, -7.3]} />

      {/* judge's platform + bench */}
      <Box args={[7.6, 0.7, 2.8]} position={[0, 0.35, -5.6]} material={mats.darkWood} />
      <Box args={[7.7, 0.05, 2.9]} position={[0, 0.72, -5.6]} material={mats.gold} cast={false} />
      <Paneled w={5.8} h={1.35} d={0.55} position={[0, 0.7, -4.45]} label={judgeName} mats={mats} />
      <Gavel strikes={gavel} />

      {/* witness box */}
      <Box args={[2.3, 0.5, 1.8]} position={[4.2, 0.25, -3.7]} material={mats.darkWood} />
      <Paneled w={2.3} h={1.1} d={0.14} position={[4.2, 0.5, -2.85]} label="Witness" mats={mats} />

      {/* the dock: a raised round platform with a gold edge */}
      <mesh position={[0, 0.15, 0.55]} castShadow receiveShadow>
        <cylinderGeometry args={[1.25, 1.35, 0.3, 48]} />
        <meshStandardMaterial color="#1a120d" roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.305, 0.55]}>
        <cylinderGeometry args={[1.26, 1.26, 0.012, 48]} />
        <meshStandardMaterial {...GOLD} />
      </mesh>

      {/* counsel tables */}
      {[-3.7, 3.7].map((x) => (
        <group key={x}>
          <Box args={[3.2, 0.08, 1.3]} position={[x, 0.98, 2.25]} material={mats.wood} />
          <Paneled w={3.2} h={0.94} d={0.06} position={[x, 0, 2.88]} label={x < 0 ? "The People" : "The Defense"} mats={mats} />
          {/* papers and a cup of courage */}
          <mesh position={[x - 0.6, 1.03, 2.2]} rotation={[-Math.PI / 2, 0, 0.2]}><planeGeometry args={[0.4, 0.55]} /><meshStandardMaterial color="#e9e1cf" /></mesh>
          <mesh position={[x + 0.8, 1.1, 2.1]} castShadow><cylinderGeometry args={[0.07, 0.06, 0.16, 16]} /><meshStandardMaterial color={x < 0 ? "#6b202a" : "#2f6f6a"} /></mesh>
        </group>
      ))}

      {/* the bar: rail between gallery and the well */}
      <Box args={[16, 0.07, 0.14]} position={[0, 0.98, 4.6]} material={mats.gold} />
      {balusters.map((x) => (
        <Box key={x} args={[0.07, 0.95, 0.07]} position={[x, 0.48, 4.6]} material={mats.darkWood} />
      ))}

      <JuryBox mats={mats} />
      <Window x={9.45} z={-4} />
      <Window x={9.45} z={1} />
      <Window x={-9.45} z={-4.8} />
      <Lamp position={[-3.6, 5.3, 0.6]} />
      <Lamp position={[0, 5.9, -2.8]} />
      <Lamp position={[3.6, 5.3, 0.6]} />
    </group>
  );
}
