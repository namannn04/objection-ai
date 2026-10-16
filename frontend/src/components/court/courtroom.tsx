"use client";

import { AnimatePresence, motion } from "motion/react";
import { FolderOpen, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { StageSwitch, useStageMode } from "@/components/court3d/stage-switch";
import type { Mode } from "@/lib/types";
import { cn } from "@/lib/utils";
import { usePlayer } from "@/stores/player";
import { ObjectionBurst, SceneTitleCard, StageExhibit } from "./hud";
import { InterventionPanel } from "./interventions";
import { PhaseStepper } from "./phase-stepper";
import { SidePanel } from "./side-panel";
import { SceneProgress, StageCaptions, StageControls, WaitingNote, useCourtKeys } from "./stage-hud";
import { useCourtroom } from "./use-courtroom";
import { VerdictCard, VerdictReveal } from "./verdict";

export function Courtroom({ caseRef, mode }: { caseRef: string; mode: Mode }) {
  const c = useCourtroom(caseRef, mode);
  const { session, manifest } = c;
  const status = usePlayer((s) => s.status);
  const seg = usePlayer((s) => s.segment);
  const reactions = usePlayer((s) => s.reactions);
  const sceneKey = usePlayer((s) => s.sceneKey);
  const loaded = usePlayer((s) => s.loaded);
  const toLoad = usePlayer((s) => s.toLoad);
  const error = usePlayer((s) => s.error);
  const burst = usePlayer((s) => s.burst);
  const gavel = usePlayer((s) => s.gavel);
  const verdictStamp = usePlayer((s) => s.verdictStamp);
  const [stageMode, setStageMode, can3d] = useStageMode();
  const [drawer, setDrawer] = useState(false);
  // Full screen shows only the courtroom; the controls fade away while the mouse rests.
  const stageRef = useRef<HTMLDivElement>(null);
  const [full, setFull] = useState(false);
  const [idle, setIdle] = useState(false);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toggleFull = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void stageRef.current?.requestFullscreen?.().catch(() => undefined);
  }, []);
  const wake = useCallback(() => {
    setIdle(false);
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => setIdle(true), 2200);
  }, []);
  useEffect(() => {
    const onChange = () => {
      const on = !!stageRef.current && document.fullscreenElement === stageRef.current;
      setFull(on);
      if (on) {
        setDrawer(false);
        wake();
      }
    };
    document.addEventListener("fullscreenchange", onChange);
    return () => {
      document.removeEventListener("fullscreenchange", onChange);
      if (idleTimer.current) clearTimeout(idleTimer.current);
    };
  }, [wake]);
  const hideChrome = full && idle;
  useCourtKeys(c.togglePause, c.jumpLine, toggleFull);
  const [startedAt, setStartedAt] = useState(() => Date.now());

  const scene = manifest?.scenes.find((s) => s.key === sceneKey);
  const witnessKey = useMemo(() => {
    if (!manifest || !scene) return null;
    if (seg && manifest.characters.find((x) => x.key === seg.speaker)?.role === "witness") return seg.speaker;
    const inScene = [...scene.segments].reverse().find((s) => manifest.characters.find((x) => x.key === s.speaker)?.role === "witness");
    return inScene?.speaker ?? null;
  }, [manifest, scene, seg]);
  const openWindowScene = manifest?.scenes.find((s) => s.key === session?.open_window);
  const showWindow = status === "interrupted" && !!openWindowScene?.window;

  if (error && status === "failed") {
    return (
      <div className="mx-auto max-w-xl py-24 text-center">
        <div className="eyebrow text-burgundy-bright">Mistrial</div>
        <h1 className="mt-4 font-display text-5xl">Something interrupted the court.</h1>
        <p className="mt-4 text-ivory-dim">{error}</p>
        <Link href={`/case/${caseRef}`} className="mt-8 inline-block rounded-full bg-gold px-6 py-3 font-semibold text-ink">Back to the case</Link>
      </div>
    );
  }
  if (!manifest) return <div className="mx-auto mt-6 aspect-[16/9] w-full max-w-[1400px] animate-pulse rounded-3xl bg-ink-2" />;

  const ready = status === "ready" || status === "idle" || status === "loading";

  return (
    <div className="mx-auto flex w-full max-w-[calc((100vh-150px)*1.7778)] flex-col">
      {/* compact top bar */}
      <header className="flex items-end justify-between gap-4 pb-3">
        <div className="min-w-0">
          <Link href={`/case/${manifest.case.slug}`} className="font-mono text-[10px] uppercase tracking-[0.2em] text-mute hover:text-ivory">
            ← {manifest.case.case_number}
          </Link>
          <h1 className="truncate font-display text-2xl leading-tight sm:text-3xl">{manifest.case.title}</h1>
        </div>
        <div className="flex shrink-0 items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em]">
          <span className="hidden rounded-full border border-line px-3 py-1.5 text-mute sm:inline">{mode} mode</span>
          {can3d && (
            <div className="flex rounded-full border border-line p-0.5" role="radiogroup" aria-label="Stage view">
              {(["3d", "2d"] as const).map((m) => (
                <button key={m} role="radio" aria-checked={stageMode === m} onClick={() => setStageMode(m)}
                  className={cn("rounded-full px-2.5 py-1 transition-colors", stageMode === m ? "bg-ivory text-ink" : "text-mute hover:text-ivory")}>
                  {m.toUpperCase()}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* the stage: everything happens in here */}
      <div
        ref={stageRef}
        onMouseMove={full ? wake : undefined}
        className={cn(
          "relative overflow-hidden bg-black",
          full ? "grid place-items-center" : "rounded-[22px] border hairline shadow-[0_50px_140px_-50px_rgba(0,0,0,1)]",
          hideChrome && "cursor-none",
        )}
      >
        <StageSwitch
          mode={stageMode}
          burst={burst}
          gavel={gavel}
          celebrate={verdictStamp}
          verdict={session?.phase === "VERDICT" && seg?.speaker === "judge"}
          segmentKind={seg?.kind}
          characters={manifest.characters}
          speaker={seg?.speaker ?? null}
          emotion={seg?.emotion}
          reactions={reactions}
          amplitude={c.amplitude}
          witnessKey={witnessKey}
          className={cn("rounded-none border-0", full && "max-h-screen max-w-[calc(100vh*16/9)]")}
          live={status === "playing"}
        >
          <SceneTitleCard />
          <StageExhibit evidence={manifest.evidence} />
          <ObjectionBurst />
          <VerdictReveal verdict={session?.verdict ?? null} />
          <StageCaptions characters={manifest.characters} hidden={showWindow} />
          <WaitingNote />
          {!full && <SceneProgress />}

          {!ready && (
            <div className={cn("absolute right-[2%] top-[3%] z-[14] flex items-center gap-2 transition-opacity duration-500",
              hideChrome && "pointer-events-none opacity-0 [&_*]:pointer-events-none")}>
              <button
                onClick={() => setDrawer((v) => !v)}
                className="pointer-events-auto flex items-center gap-2 rounded-full border border-white/10 bg-ink/55 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.16em] text-ivory/85 backdrop-blur-md transition-colors hover:text-ivory"
                aria-expanded={drawer}
              >
                <FolderOpen className="h-3.5 w-3.5" /> Case file
              </button>
              <StageControls onToggle={c.togglePause} onJump={c.jumpLine} onVolume={c.setVolume} onFullscreen={toggleFull} fullscreen={full} />
            </div>
          )}

          {/* intervention window, inside the stage */}
          <AnimatePresence>
            {showWindow && openWindowScene?.window && (
              <div className="absolute inset-x-[3%] bottom-[4%] z-[15] max-h-[88%] overflow-y-auto">
                <InterventionPanel
                  key={openWindowScene.key}
                  window={openWindowScene.window}
                  mode={mode}
                  onChoose={c.choose}
                  onSkip={c.skipWindow}
                  onFreeText={c.intervene}
                />
              </div>
            )}
          </AnimatePresence>

          {/* the case file slides over the stage */}
          <AnimatePresence>
            {drawer && !ready && (
              <motion.div
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", stiffness: 260, damping: 30 }}
                className="absolute inset-y-0 right-0 z-[16] flex w-[min(360px,92%)] flex-col bg-ink/85 p-3 backdrop-blur-xl"
              >
                <button onClick={() => setDrawer(false)} aria-label="Close case file"
                  className="mb-2 ml-auto grid h-8 w-8 place-items-center rounded-full text-mute hover:bg-white/10 hover:text-ivory">
                  <X className="h-4 w-4" />
                </button>
                <div className="min-h-0 flex-1"><SidePanel manifest={manifest} session={session} /></div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* the gate */}
          <AnimatePresence>
            {ready && (
              <motion.div className="absolute inset-0 z-[20] grid place-items-center bg-ink/70 backdrop-blur-[3px]" exit={{ opacity: 0 }}>
                <div className="text-center">
                  <div className="eyebrow">{manifest.audio.ready ? "The court is ready" : "Some audio is missing"}</div>
                  <div className="mt-3 font-display text-[clamp(1.6rem,4vw,3rem)] leading-tight">{manifest.case.title}</div>
                  <button
                    onClick={c.begin}
                    disabled={status === "loading" || !session}
                    className="mt-6 rounded-full bg-gold px-10 py-4 font-display text-3xl italic text-ink shadow-[0_20px_60px_-15px_rgb(214_174_98/0.7)] transition-transform hover:scale-[1.03] disabled:opacity-70"
                  >
                    {status === "loading" ? `Preparing… ${loaded}/${toLoad}` : "All rise"}
                  </button>
                  <p className="mt-4 text-xs text-mute">Sound on · Space pause · ← → skip lines · F full screen · C captions</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </StageSwitch>
      </div>

      {/* the docket: progress through the trial */}
      <div className="mt-4 px-1">
        <PhaseStepper manifest={manifest} session={session} />
      </div>

      {status === "completed" && session?.verdict && (
        <VerdictCard verdict={session.verdict} manifest={manifest} mode={mode} startedAt={startedAt}
          onReplay={(m) => { setStartedAt(Date.now()); void c.replay(m); }} />
      )}
    </div>
  );
}
