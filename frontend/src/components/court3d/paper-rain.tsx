"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

const COUNT = 90;

/** When the verdict lands, case papers flutter down through the light. */
export function PaperRain({ active }: { active: boolean }) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const seeds = useMemo(
    () => Array.from({ length: COUNT }, (_, i) => ({
      x: Math.abs((Math.sin(i * 12.9898) * 43758.5453) % 1) * 12 - 6,
      z: Math.abs((Math.sin(i * 78.233) * 12345.678) % 1) * 8 - 4,
      delay: (i % 30) * 0.08,
      spin: 1 + (i % 7) * 0.4,
      sway: 0.6 + (i % 5) * 0.25,
    })),
    [],
  );
  const start = useRef<number | null>(null);
  useFrame(({ clock }) => {
    if (!mesh.current) return;
    if (!active) {
      start.current = null;
      mesh.current.visible = false;
      return;
    }
    if (start.current === null) start.current = clock.elapsedTime;
    mesh.current.visible = true;
    const t = clock.elapsedTime - start.current;
    seeds.forEach((s, i) => {
      const life = Math.max(0, t - s.delay);
      const y = Math.max(0.02, 7.5 - life * 1.1);
      const landed = y <= 0.02;
      dummy.position.set(s.x + Math.sin(life * s.sway) * 0.6, y, s.z + Math.cos(life * s.sway * 0.8) * 0.4);
      dummy.rotation.set(landed ? -Math.PI / 2 : Math.sin(life * s.spin) * 1.2, life * s.spin * 0.6, landed ? 0 : Math.cos(life * s.spin) * 0.8);
      dummy.updateMatrix();
      mesh.current!.setMatrixAt(i, dummy.matrix);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
  });
  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, COUNT]} castShadow visible={false}>
      <planeGeometry args={[0.22, 0.3]} />
      <meshStandardMaterial color="#efe7d6" side={THREE.DoubleSide} roughness={0.9} />
    </instancedMesh>
  );
}
