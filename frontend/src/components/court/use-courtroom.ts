"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, mediaUrl } from "@/lib/api";
import { CourtAudioEngine, type Timeline } from "@/lib/audio-engine";
import type { Manifest, Mode, Scene, Segment, SessionState } from "@/lib/types";
import { PHASE_LABEL } from "@/lib/utils";
import { usePlayer } from "@/stores/player";

const segUrl = (s: Segment) => (s.audio ? mediaUrl(s.audio.url) : null);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function allUrls(m: Manifest): string[] {
  const urls: string[] = [];
  for (const sc of m.scenes) {
    for (const s of sc.segments) if (s.audio) urls.push(mediaUrl(s.audio.url));
    for (const o of sc.window?.options ?? []) for (const s of o.response) if (s.audio) urls.push(mediaUrl(s.audio.url));
  }
  return urls;
}

/**
 * The courtroom controller. The server owns the trial state (phases, windows,
 * verdict); this hook plays prepared audio and reports scene completion.
 */
export function useCourtroom(caseRef: string, mode: Mode) {
  const set = usePlayer((s) => s.set);
  const engine = useRef<CourtAudioEngine | null>(null);
  const timeline = useRef<Timeline | null>(null);
  const queueKind = useRef<"scene" | "response" | null>(null);
  const busy = useRef(false);
  const lastBurstSeg = useRef<string | null>(null);
  const lastGavelAt = useRef(-1);
  const [session, setSession] = useState<SessionState | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const sessionRef = useRef<SessionState | null>(null);
  const manifestRef = useRef<Manifest | null>(null);
  useEffect(() => {
    sessionRef.current = session;
  }, [session]);
  useEffect(() => {
    manifestRef.current = manifest;
  }, [manifest]);

  const fail = useCallback((e: unknown) => set({ status: "failed", error: e instanceof Error ? e.message : String(e) }), [set]);

  // Open a session as soon as the page mounts.
  useEffect(() => {
    let alive = true;
    usePlayer.setState({ status: "idle", error: null, verdictStamp: false, titleCard: null, segment: null, sceneKey: null });
    api.openSession(caseRef, mode).then(
      (r) => {
        if (!alive) return;
        sessionRef.current = r.state;
        manifestRef.current = r.manifest;
        setSession(r.state);
        setManifest(r.manifest);
        set({ status: "ready" });
      },
      (e) => alive && fail(e),
    );
    return () => {
      alive = false;
      engine.current?.dispose();
      engine.current = null;
    };
  }, [caseRef, mode, set, fail]);

  const findScene = (key: string | null): Scene | undefined => manifestRef.current?.scenes.find((s) => s.key === key);

  const playQueue = useCallback(
    async (segments: Segment[], kind: "scene" | "response", scene: Scene) => {
      const eng = engine.current!;
      const missing = segments.map(segUrl).filter((u): u is string => !!u && !eng.has(u));
      if (missing.length) {
        set({ status: "buffering" });
        await eng.preload(missing);
      }
      const tl = eng.compile(segments, segUrl);
      timeline.current = tl;
      queueKind.current = kind;
      lastBurstSeg.current = null;
      lastGavelAt.current = -1;
      set({ sceneKey: scene.key, sceneTitle: scene.title, queueKind: kind, duration: tl.duration, position: 0, segIndex: -1, segment: null, status: "playing" });
      await eng.resume();
      eng.play(tl, segUrl, 0);
    },
    [set],
  );

  const playScene = useCallback(
    async (key: string | null) => {
      const scene = findScene(key);
      if (!scene) return fail(new Error(`scene ${key} missing from manifest`));
      const prev = findScene(usePlayer.getState().sceneKey);
      if (!prev || prev.phase !== scene.phase || scene.branch) {
        set({ titleCard: { phase: scene.branch ? "The Verdict" : PHASE_LABEL[scene.phase], title: scene.title }, status: "buffering", segment: null });
        await sleep(1500);
        set({ titleCard: null });
      }
      await playQueue(scene.segments, "scene", scene);
    },
    [playQueue, set, fail],
  );

  const route = useCallback(
    async (st: SessionState) => {
      sessionRef.current = st;
      setSession(st);
      if (st.phase === "CASE_COMPLETED") {
        set({ status: "completed", segment: null });
        return;
      }
      if (st.open_window) {
        set({ status: "interrupted", segment: null });
        return;
      }
      if (st.phase === "VERDICT" && st.verdict_scene) return playScene(st.verdict_scene);
      if (st.next_scene) return playScene(st.next_scene);
    },
    [playScene, set],
  );

  const onQueueEnd = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const sid = sessionRef.current!.session_id;
      const key = usePlayer.getState().sceneKey!;
      set({ status: "buffering" });
      const st = queueKind.current === "response" ? await api.resolve(sid) : await api.completeScene(sid, key);
      await route(st);
    } catch (e) {
      fail(e);
    } finally {
      busy.current = false;
    }
  }, [route, set, fail]);

  // Frame loop: derive the active line, word, reactions and evidence from the audio clock.
  useEffect(() => {
    let raf = 0;
    let lastPos = 0;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      const eng = engine.current;
      const tl = timeline.current;
      const st = usePlayer.getState();
      if (!eng || !tl || st.status !== "playing") return;
      const pos = eng.position();
      let idx = -1;
      for (let i = 0; i < tl.items.length; i++) if (tl.items[i].start <= pos) idx = i;
      const item = idx >= 0 ? tl.items[idx] : null;
      const live = item && pos < item.end;
      const seg = live ? item.seg : null;
      const after = item ? pos - item.end : 0;
      let word = -1;
      if (seg?.audio) {
        const ms = (pos - item!.start) * 1000;
        const words = seg.audio.words;
        for (let w = 0; w < words.length; w++) if (words[w].s <= ms) word = w;
      }
      const reactions = item && after < 0.9 ? item.seg.reactions : {};
      const evidenceId = item && after < 1.6 ? item.seg.evidence_id : null;
      const patch: Partial<ReturnType<typeof usePlayer.getState>> = {};
      if (idx !== st.segIndex) patch.segIndex = idx;
      if ((seg?.turn_key ?? null) !== (st.segment?.turn_key ?? null)) patch.segment = seg;
      if (word !== st.wordIndex) patch.wordIndex = word;
      if (reactions !== st.reactions) patch.reactions = reactions;
      if (evidenceId !== st.evidenceId) patch.evidenceId = evidenceId;
      // OBJECTION! burst when a line with an objection sting comes up
      const next = tl.items[idx + 1];
      const upcoming = next && next.seg.sfx_before.includes("objection") && pos >= next.start - 0.62 ? next.seg : null;
      if (upcoming && lastBurstSeg.current !== upcoming.turn_key) {
        lastBurstSeg.current = upcoming.turn_key;
        patch.burst = st.burst + 1;
      }
      if (item && item.seg.kind === "verdict" && after > 0 && !st.verdictStamp) patch.verdictStamp = true;
      for (const cue of tl.cues) {
        if (cue.name === "gavel" && cue.at > lastGavelAt.current && cue.at <= pos && pos - cue.at < 0.5) {
          lastGavelAt.current = cue.at;
          patch.gavel = st.gavel + 1;
        }
      }
      if (Math.abs(pos - lastPos) > 0.1) {
        patch.position = Math.min(pos, tl.duration);
        lastPos = pos;
      }
      if (Object.keys(patch).length) st.set(patch);
      if (pos >= tl.duration) void onQueueEnd();
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [onQueueEnd]);

  /** "All rise": needs a user gesture to start audio. Preloads everything first. */
  const begin = useCallback(async () => {
    const m = manifestRef.current;
    const s = sessionRef.current;
    if (!m || !s) return;
    try {
      if (!engine.current) {
        engine.current = new CourtAudioEngine();
        engine.current.setVolume(usePlayer.getState().volume);
        engine.current.sfxUrls = Object.fromEntries(Object.entries(m.sfx).map(([k, v]) => [k, mediaUrl(v)]));
      }
      const urls = [...Object.values(engine.current.sfxUrls).filter(Boolean) as string[], ...allUrls(m)];
      set({ status: "loading", loaded: 0, toLoad: urls.length });
      await engine.current.resume();
      await engine.current.preload(urls, (d, t) => set({ loaded: d, toLoad: t }));
      const st = s.phase === "COURTROOM_READY" ? await api.start(s.session_id) : s;
      await route(st);
    } catch (e) {
      fail(e);
    }
  }, [route, set, fail]);

  const togglePause = useCallback(async () => {
    const eng = engine.current;
    const st = usePlayer.getState();
    if (!eng) return;
    if (st.status === "playing") {
      await eng.pause();
      set({ status: "paused" });
    } else if (st.status === "paused") {
      await eng.resume();
      set({ status: "playing" });
    }
  }, [set]);

  const seek = useCallback((sec: number) => {
    const eng = engine.current;
    const tl = timeline.current;
    if (!eng || !tl) return;
    eng.play(tl, segUrl, Math.max(0, Math.min(sec, tl.duration - 0.05)));
    lastBurstSeg.current = null;
    if (usePlayer.getState().status === "paused") void eng.resume().then(() => set({ status: "playing" }));
  }, [set]);

  const jumpLine = useCallback((delta: -1 | 0 | 1) => {
    const tl = timeline.current;
    if (!tl) return;
    const cur = usePlayer.getState().segIndex;
    if (delta === 1 && cur >= tl.items.length - 1) {
      seek(tl.duration - 0.05); // skipping past the last line finishes the scene
      return;
    }
    const i = Math.max(0, Math.min(tl.items.length - 1, cur + delta));
    seek(tl.items[i].start - 0.05);
  }, [seek]);

  const setVolume = useCallback((v: number) => {
    engine.current?.setVolume(v);
    set({ volume: v });
  }, [set]);

  const choose = useCallback(async (optionId: string) => {
    const s = sessionRef.current;
    const scene = findScene(s?.open_window ?? null);
    const opt = scene?.window?.options.find((o) => o.id === optionId);
    if (!s || !scene || !opt) return;
    if (scene.window?.kind === "objection") {
      engine.current?.fx("objection");
      set({ burst: usePlayer.getState().burst + 1 });
    }
    try {
      set({ status: "buffering" });
      const r = await api.choose(s.session_id, scene.key, optionId);
      setSession(r.state);
      if (opt.response.length) {
        if (scene.window?.kind === "objection") await sleep(700);
        await playQueue(opt.response, "response", scene);
      } else {
        await route(await api.resolve(s.session_id));
      }
    } catch (e) {
      fail(e);
    }
  }, [playQueue, route, set, fail]);

  const skipWindow = useCallback(async () => {
    const s = sessionRef.current;
    if (!s) return;
    try {
      set({ status: "buffering" });
      await route(await api.resolve(s.session_id));
    } catch (e) {
      fail(e);
    }
  }, [route, set, fail]);

  /** Chaos mode: a free-text intervention is generated live, then played. */
  const intervene = useCallback(async (text: string) => {
    const s = sessionRef.current;
    const sceneKey = s?.open_window;
    if (!s || !sceneKey) return;
    engine.current?.fx("objection");
    set({ burst: usePlayer.getState().burst + 1, status: "buffering" });
    try {
      const r = await api.intervene(s.session_id, sceneKey, text);
      setSession(r.state);
      if (r.job_id) {
        for (let i = 0; i < 240; i++) {
          const job = await api.job(r.job_id);
          if (job.status === "done" || job.status === "blocked") break;
          if (job.status === "failed") throw new Error(job.error ?? "The court could not respond.");
          await sleep(500);
        }
      }
      const m = await api.manifest(caseRef, s.session_id);
      setManifest(m);
      manifestRef.current = m;
      const scene = m.scenes.find((x) => x.key === sceneKey)!;
      const branch = scene.live_branches[`live-${r.intervention_id}`] ?? [];
      if (!branch.length) throw new Error("The court had no response prepared.");
      await playQueue(branch, "response", scene);
    } catch (e) {
      fail(e);
    }
  }, [caseRef, playQueue, set, fail]);

  const replay = useCallback(async (newMode?: Mode) => {
    const s = sessionRef.current;
    if (!s) return;
    const r = await api.replay(s.session_id, newMode);
    setSession(r.state);
    setManifest(r.manifest);
    manifestRef.current = r.manifest;
    sessionRef.current = r.state;
    usePlayer.setState({ verdictStamp: false, sceneKey: null, segment: null });
    await route(await api.start(r.state.session_id));
  }, [route]);

  return {
    session, manifest, begin, togglePause, seek, jumpLine, setVolume, choose, skipWindow, intervene, replay,
    amplitude: () => engine.current?.amplitude() ?? 0,
  };
}
