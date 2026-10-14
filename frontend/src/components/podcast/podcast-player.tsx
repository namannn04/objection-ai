"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Pause, Play } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type WaveSurfer from "wavesurfer.js";
import { CharacterPortrait } from "@/components/characters/character-portrait";
import { api, mediaUrl, type Podcast } from "@/lib/api";
import { cn, formatMs } from "@/lib/utils";

const SPEEDS = [0.75, 1, 1.25, 1.5];

export function PodcastStudio({ caseRef }: { caseRef: string }) {
  const qc = useQueryClient();
  const manifest = useQuery({ queryKey: ["manifest", caseRef], queryFn: () => api.manifest(caseRef) });
  const episodes = useQuery({
    queryKey: ["podcasts", caseRef],
    queryFn: () => api.casePodcasts(caseRef),
    refetchInterval: (q) => (q.state.data?.some((e) => e.status !== "ready" && e.status !== "failed") ? 1500 : false),
  });
  const [selected, setSelected] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: (verdict: "guilty" | "not_guilty") => api.createPodcast(caseRef, { verdict }),
    onSuccess: (r) => {
      setSelected(r.id);
      void qc.invalidateQueries({ queryKey: ["podcasts", caseRef] });
    },
  });
  const list = episodes.data ?? [];
  const ep = list.find((e) => e.id === selected) ?? list.find((e) => e.status === "ready");
  const m = manifest.data;

  return (
    <div className="mx-auto w-full max-w-[1200px]">
      <Link href={`/case/${caseRef}`} className="font-mono text-[10px] uppercase tracking-[0.2em] text-mute hover:text-ivory">← Back to the case</Link>
      <div className="mt-6 grid gap-10 lg:grid-cols-[320px_1fr]">
        <div>
          <div className="relative aspect-square overflow-hidden rounded-3xl border hairline bg-[radial-gradient(circle_at_50%_25%,#3a2c1c,#0d0c0b_70%)]">
            <div className="absolute inset-x-[18%] bottom-[18%] top-[14%]">
              {m && <CharacterPortrait character={m.characters.find((c) => c.role === "defendant")!} />}
            </div>
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink via-ink/80 to-transparent p-5">
              <div className="font-mono text-[9px] uppercase tracking-[0.25em] text-gold">The Court of Absolute Nonsense</div>
              <div className="mt-1 font-display text-2xl leading-tight">{m?.case.title ?? "…"}</div>
            </div>
          </div>
          <div className="mt-6 eyebrow">Record a new episode</div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {(["guilty", "not_guilty"] as const).map((v) => (
              <button key={v} disabled={create.isPending} onClick={() => create.mutate(v)}
                className="rounded-xl border border-line-strong px-3 py-3 text-sm transition-colors hover:border-gold hover:text-gold disabled:opacity-50">
                {v === "guilty" ? "Guilty ending" : "Not guilty ending"}
              </button>
            ))}
          </div>
          {create.isError && <p className="mt-2 text-sm text-burgundy-bright">{(create.error as Error).message}</p>}
          <div className="mt-8 eyebrow">Episode history</div>
          <ul className="mt-3 space-y-2">
            {list.map((e) => (
              <li key={e.id}>
                <button onClick={() => setSelected(e.id)}
                  className={cn("w-full rounded-xl border px-4 py-3 text-left text-sm transition-colors",
                    ep?.id === e.id ? "border-gold/60 bg-gold/5" : "border-line hover:border-line-strong")}>
                  <div className="truncate">{e.title}</div>
                  <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-mute">
                    {e.status === "ready" ? formatMs(e.duration_ms) : `${e.status}…`}
                  </div>
                </button>
              </li>
            ))}
            {!list.length && !episodes.isLoading && <li className="text-sm text-mute">No episodes yet. Record one above — it mixes the whole trial into a single file.</li>}
          </ul>
        </div>
        <div>
          <div className="eyebrow">Podcast mode</div>
          <h1 className="mt-3 font-display text-[clamp(2.6rem,5vw,4.6rem)] leading-[0.92]">{ep?.title ?? m?.case.title}</h1>
          {ep && ep.status === "ready" ? <Episode ep={ep} /> : (
            <div className="mt-10 grid h-64 place-items-center rounded-3xl border border-dashed border-line-strong text-center text-mute">
              {list.some((e) => e.status !== "ready") ? "Mixing the episode… (gavels are being calibrated)" : "Record an episode to listen."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Episode({ ep }: { ep: Podcast }) {
  const el = useRef<HTMLDivElement>(null);
  const ws = useRef<WaveSurfer | null>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [ready, setReady] = useState(false);
  const transcriptRef = useRef<HTMLOListElement>(null);

  useEffect(() => {
    let destroyed = false;
    let inst: WaveSurfer | null = null;
    void import("wavesurfer.js").then(({ default: WS }) => {
      if (destroyed || !el.current) return;
      inst = WS.create({
        container: el.current, url: mediaUrl(ep.mp3_url!), height: 84, waveColor: "#3a352d", progressColor: "#d6ae62",
        cursorColor: "#f5f0e6", barWidth: 2, barGap: 2, barRadius: 2, normalize: true,
      });
      inst.on("ready", () => setReady(true));
      inst.on("timeupdate", (s) => setT(s * 1000));
      inst.on("play", () => setPlaying(true));
      inst.on("pause", () => setPlaying(false));
      ws.current = inst;
    });
    return () => {
      destroyed = true;
      inst?.destroy();
      ws.current = null;
      setReady(false);
    };
  }, [ep.mp3_url]);

  const active = ep.transcript.findIndex((x) => t >= x.start_ms && t < x.end_ms);
  useEffect(() => {
    if (active < 0) return;
    transcriptRef.current?.children[active]?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [active]);
  const seek = (ms: number) => ws.current?.setTime(ms / 1000);

  return (
    <div className="mt-8">
      <div className="rounded-3xl border hairline bg-ink-2 p-5">
        <div ref={el} className={cn("transition-opacity", ready ? "opacity-100" : "opacity-30")} />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button onClick={() => ws.current?.playPause()} disabled={!ready} aria-label={playing ? "Pause" : "Play"}
            className="grid h-12 w-12 place-items-center rounded-full bg-gold text-ink disabled:opacity-50">
            {playing ? <Pause className="h-5 w-5 fill-current" /> : <Play className="h-5 w-5 translate-x-px fill-current" />}
          </button>
          <span className="font-mono text-xs text-mute">{formatMs(t)} / {formatMs(ep.duration_ms)}</span>
          <div className="ml-auto flex items-center gap-1">
            {SPEEDS.map((s) => (
              <button key={s} onClick={() => { setSpeed(s); ws.current?.setPlaybackRate(s, true); }}
                className={cn("rounded-full px-2.5 py-1 font-mono text-[11px]", speed === s ? "bg-ivory text-ink" : "text-mute hover:text-ivory")}>
                {s}×
              </button>
            ))}
          </div>
          <a href={mediaUrl(ep.mp3_url!)} download className="inline-flex items-center gap-1.5 rounded-full border border-line-strong px-3 py-1.5 text-xs hover:bg-white/5">
            <Download className="h-3.5 w-3.5" /> MP3
          </a>
          {ep.wav_url && (
            <a href={mediaUrl(ep.wav_url)} download className="inline-flex items-center gap-1.5 rounded-full border border-line-strong px-3 py-1.5 text-xs hover:bg-white/5">
              <Download className="h-3.5 w-3.5" /> WAV
            </a>
          )}
        </div>
      </div>
      <div className="mt-8 grid gap-8 md:grid-cols-[220px_1fr]">
        <div>
          <div className="eyebrow">Chapters</div>
          <ol className="mt-3 space-y-1">
            {ep.chapters.map((c, i) => {
              const on = t >= c.start_ms && (i === ep.chapters.length - 1 || t < ep.chapters[i + 1].start_ms);
              return (
                <li key={i}>
                  <button onClick={() => seek(c.start_ms)} className={cn("w-full rounded-lg px-3 py-2 text-left text-sm transition-colors", on ? "bg-gold/10 text-gold" : "text-ivory-dim hover:bg-white/5")}>
                    <span className="mr-2 font-mono text-[10px] text-mute">{formatMs(c.start_ms)}</span>{c.title}
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
        <div>
          <div className="eyebrow">Transcript</div>
          <ol ref={transcriptRef} className="mt-3 max-h-[480px] space-y-3 overflow-y-auto pr-2">
            {ep.transcript.map((x, i) => (
              <li key={x.turn_key}>
                <button onClick={() => seek(x.start_ms)} className={cn("w-full rounded-xl px-4 py-3 text-left transition-colors", i === active ? "bg-ink-3" : "hover:bg-white/[0.03]")}>
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold">{x.name} <span className="text-mute">· {formatMs(x.start_ms)}</span></div>
                  <p className={cn("mt-1 leading-relaxed", i === active ? "text-ivory" : "text-ivory-dim")}>{x.text}</p>
                </button>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
