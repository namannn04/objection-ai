"use client";

import dynamic from "next/dynamic";
import { Component, useEffect, useState, type ReactNode } from "react";
import { CourtroomStage, type StageProps } from "@/components/court/courtroom-stage";
import type { Courtroom3DProps } from "./courtroom-3d";

const Courtroom3D = dynamic(() => import("./courtroom-3d"), { ssr: false, loading: () => null });

export type StageMode = "3d" | "2d";

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

/** Remembers the viewer's 2D/3D choice; 3D is the default when the device can do it. */
export function useStageMode(): [StageMode, (m: StageMode) => void, boolean] {
  const [mode, setMode] = useState<StageMode>("2d");
  const [capable, setCapable] = useState(false);
  useEffect(() => {
    const ok = webglAvailable();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let saved: string | null = null;
    try {
      saved = localStorage.getItem("objection.stage");
    } catch {
      /* storage unavailable */
    }
    const id = setTimeout(() => {
      setCapable(ok);
      setMode(ok && (saved ? saved === "3d" : !reduce) ? "3d" : "2d");
    }, 0);
    return () => clearTimeout(id);
  }, []);
  const set = (m: StageMode) => {
    setMode(m);
    try {
      localStorage.setItem("objection.stage", m);
    } catch {
      /* storage unavailable */
    }
  };
  return [mode, set, capable];
}

class Fallback extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export function StageSwitch({ mode, ...props }: StageProps & Pick<Courtroom3DProps, "burst" | "verdict" | "segmentKind" | "showcase"> & { mode: StageMode }) {
  const { burst, verdict, segmentKind, showcase, ...flat } = props;
  const flatStage = <CourtroomStage {...flat} />;
  if (mode === "2d") return flatStage;
  return (
    <Fallback fallback={flatStage}>
      <Courtroom3D {...flat} burst={burst} verdict={verdict} segmentKind={segmentKind} showcase={showcase} />
    </Fallback>
  );
}
