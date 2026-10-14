"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { StageSwitch, useStageMode } from "@/components/court3d/stage-switch";
import type { Mode } from "@/lib/types";
import { cn, PHASE_LABEL } from "@/lib/utils";
import { usePlayer } from "@/stores/player";
import { AudioTimeline, DialogueSubtitle, ObjectionBurst, SceneTitleCard, StageExhibit } from "./hud";
import { InterventionPanel, ObjectionButton } from "./interventions";
import { SidePanel } from "./side-panel";
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
  const [stageMode, setStageMode, can3d] = useStageMode();
  const [startedAt, setStartedAt] = useState(() => Date.now());

  const scene = manifest?.scenes.find((s) => s.key === sceneKey);
  const witnessKey = useMemo(() => {
    if (!manifest || !scene) return null;
    const inScene = [...scene.segments].reverse().find((s) => manifest.characters.find((c2) => c2.key === s.speaker)?.role === "witness");
    if (seg && manifest.characters.find((c2) => c2.key === seg.speaker)?.role === "witness") return seg.speaker;
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
  if (!manifest) return <div className="mx-auto mt-10 aspect-[16/9] w-full max-w-[1400px] animate-pulse rounded-3xl bg-ink-2" />;

  const ready = status === "ready" || status === "idle" || status === "loading";

  return (
    <div className="mx-auto w-full max-w-[1500px]">
      <header className="flex flex-wrap items-center justify-between gap-3 pb-4">
        <div className="min-w-0">
          <Link href={`/case/${manifest.case.slug}`} className="font-mono text-[10px] uppercase tracking-[0.2em] text-mute hover:text-ivory">← {manifest.case.case_number}</Link>
          <h1 className="truncate font-display text-3xl leading-tight sm:text-4xl">{manifest.case.title}</h1>
        </div>
        <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.18em]">
          <span className="flex items-center gap-2 rounded-full border border-line-strong px-3 py-1.5 text-ivory">
            <span className={cn("h-1.5 w-1.5 rounded-full", status === "playing" ? "bg-burgundy-bright animate-blink" : "bg-mute")} />
            {PHASE_LABEL[session?.phase ?? "COURTROOM_READY"]}
          </span>
          <span className="rounded-full border border-line px-3 py-1.5 text-mute">{mode} mode</span>
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

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="overflow-hidden rounded-[20px] border hairline bg-ink-2">
          <div className="mx-auto w-full lg:max-w-[calc((100vh-330px)*1.7778)]">
          <StageSwitch
            mode={stageMode}
            burst={burst}
            verdict={session?.phase === "VERDICT" && seg?.speaker === "judge"}
            segmentKind={seg?.kind}
            characters={manifest.characters}
            speaker={seg?.speaker ?? null}
            emotion={seg?.emotion}
            reactions={reactions}
            amplitude={c.amplitude}
            witnessKey={witnessKey}
            caseNumber={manifest.case.case_number}
            className="rounded-none border-0"
            live={status === "playing"}
          >
            <SceneTitleCard />
            <StageExhibit evidence={manifest.evidence} />
            <ObjectionBurst />
            <VerdictReveal verdict={session?.verdict ?? null} />
            <AnimatePresence>
              {ready && (
                <motion.div className="absolute inset-0 grid place-items-center bg-ink/75 backdrop-blur-[2px]" exit={{ opacity: 0 }}>
                  <div className="text-center">
                    <div className="eyebrow">{manifest.audio.ready ? "The court is ready" : "Some audio is missing"}</div>
                    <button
                      onClick={c.begin}
                      disabled={status === "loading" || !session}
                      className="mt-5 rounded-full bg-gold px-10 py-5 font-display text-3xl italic text-ink shadow-[0_20px_60px_-15px_rgb(214_174_98/0.7)] transition-transform hover:scale-[1.03] disabled:opacity-70"
                    >
                      {status === "loading" ? `Preparing… ${loaded}/${toLoad}` : "All rise"}
                    </button>
                    <p className="mt-4 text-xs text-mute">Sound on. Space to pause · ← → to skip lines · R to replay.</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </StageSwitch>
          </div>
          <div className="relative">
            <DialogueSubtitle characters={manifest.characters} />
            <AnimatePresence>
              {showWindow && openWindowScene?.window && (
                <div className="absolute inset-x-3 bottom-3 z-10 sm:inset-x-5">
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
          </div>
          <AudioTimeline onToggle={c.togglePause} onSeek={c.seek} onJump={c.jumpLine} onVolume={c.setVolume} />
        </div>

        <div className="flex flex-col gap-4 lg:h-[calc(100vh-150px)] lg:max-h-[860px]">
          <ObjectionButton
            mode={mode}
            armed={showWindow && openWindowScene?.window?.kind === "objection"}
            onPress={() => document.querySelector<HTMLButtonElement>("[role=dialog] button.animate-pulse-gold")?.click()}
          />
          <div className="min-h-0 flex-1"><SidePanel manifest={manifest} session={session} /></div>
        </div>
      </div>

      {status === "completed" && session?.verdict && (
        <VerdictCard verdict={session.verdict} manifest={manifest} mode={mode} startedAt={startedAt}
          onReplay={(m) => { setStartedAt(Date.now()); void c.replay(m); }} />
      )}
    </div>
  );
}
