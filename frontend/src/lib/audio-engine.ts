/**
 * CourtAudioEngine — Web Audio playback for prepared courtroom audio.
 *
 * A scene is compiled into a timeline (voice lines + SFX cues) and scheduled
 * sample-accurately against the AudioContext clock, so lines play gaplessly.
 * Pausing suspends the context (the timeline freezes with it); seeking
 * reschedules from an offset. An AnalyserNode on the voice bus feeds mouths.
 */
import type { Segment, Sfx } from "./types";

export interface TimelineItem {
  seg: Segment;
  start: number; // seconds from scene start
  end: number;
}
export interface SfxCue {
  name: Sfx;
  at: number;
  gain: number;
}
export interface Timeline {
  items: TimelineItem[];
  cues: SfxCue[];
  duration: number;
}

const LEAD: Partial<Record<Sfx, number>> = { objection: 0.62, gavel: 0.5, dramatic_sting: 0.95, crowd_murmur: 0.15 };
const SFX_GAIN: Record<Sfx, number> = {
  gavel: 0.75, objection: 0.7, crowd_gasp: 0.45, crowd_laugh: 0.4, crowd_murmur: 0.35, dramatic_sting: 0.55,
};

export class CourtAudioEngine {
  ctx: AudioContext;
  private master: GainNode;
  private voiceBus: GainNode;
  private sfxBus: GainNode;
  private analyser: AnalyserNode;
  private data: Float32Array<ArrayBuffer>;
  private buffers = new Map<string, AudioBuffer>();
  private pending = new Map<string, Promise<AudioBuffer>>();
  private sources = new Set<AudioScheduledSourceNode>();
  private t0 = 0;
  timeline: Timeline = { items: [], cues: [], duration: 0 };
  sfxUrls: Partial<Record<Sfx, string>> = {};

  constructor() {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.ctx = new Ctx({ latencyHint: "playback" });
    this.master = this.ctx.createGain();
    this.voiceBus = this.ctx.createGain();
    this.sfxBus = this.ctx.createGain();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.analyser.smoothingTimeConstant = 0.4;
    this.data = new Float32Array(this.analyser.fftSize);
    this.voiceBus.connect(this.analyser);
    this.analyser.connect(this.master);
    this.sfxBus.connect(this.master);
    this.master.connect(this.ctx.destination);
  }

  async load(url: string): Promise<AudioBuffer> {
    const hit = this.buffers.get(url);
    if (hit) return hit;
    let p = this.pending.get(url);
    if (!p) {
      p = fetch(url)
        .then((r) => {
          if (!r.ok) throw new Error(`audio ${r.status}: ${url}`);
          return r.arrayBuffer();
        })
        .then((ab) => this.ctx.decodeAudioData(ab))
        .then((b) => {
          this.buffers.set(url, b);
          return b;
        });
      this.pending.set(url, p);
    }
    return p;
  }

  async preload(urls: string[], onProgress?: (done: number, total: number) => void, concurrency = 6) {
    const unique = [...new Set(urls)];
    let done = 0;
    const queue = [...unique];
    const errors: string[] = [];
    const worker = async () => {
      while (queue.length) {
        const u = queue.shift()!;
        try {
          await this.load(u);
        } catch (e) {
          errors.push(String(e));
        }
        onProgress?.(++done, unique.length);
      }
    };
    await Promise.all(Array.from({ length: Math.min(concurrency, unique.length) }, worker));
    if (errors.length) throw new Error(`${errors.length} audio file(s) failed to load`);
  }

  has(url: string) {
    return this.buffers.has(url);
  }

  /** Compile segments into an absolute timeline using the *decoded* durations. */
  compile(segments: Segment[], url: (s: Segment) => string | null): Timeline {
    const items: TimelineItem[] = [];
    const cues: SfxCue[] = [];
    let cursor = 0.15;
    for (const seg of segments) {
      cursor += seg.gap_before_ms / 1000;
      let lead = 0;
      for (const fx of seg.sfx_before) {
        cues.push({ name: fx, at: cursor, gain: SFX_GAIN[fx] });
        lead = Math.max(lead, LEAD[fx] ?? 0.3);
      }
      const start = cursor + lead;
      const u = url(seg);
      const buf = u ? this.buffers.get(u) : undefined;
      const dur = buf ? buf.duration : (seg.audio?.duration_ms ?? 1500) / 1000;
      const end = start + dur;
      items.push({ seg, start, end });
      let tail = 0;
      for (const fx of seg.sfx_after) {
        cues.push({ name: fx, at: end - 0.12, gain: SFX_GAIN[fx] });
        tail = Math.max(tail, fx === "crowd_laugh" ? 0.9 : 0.55);
      }
      cursor = end + tail;
    }
    return { items, cues, duration: cursor + 0.35 };
  }

  play(timeline: Timeline, url: (s: Segment) => string | null, from = 0) {
    this.stopAll();
    this.timeline = timeline;
    const now = this.ctx.currentTime + 0.06;
    this.t0 = now - from;
    for (const it of timeline.items) {
      if (it.end <= from) continue;
      const u = url(it.seg);
      const buf = u ? this.buffers.get(u) : undefined;
      if (!buf) continue;
      const src = this.ctx.createBufferSource();
      src.buffer = buf;
      src.connect(this.voiceBus);
      const offset = Math.max(0, from - it.start);
      src.start(this.t0 + it.start + offset, offset);
      this.track(src);
    }
    for (const c of timeline.cues) {
      if (c.at < from - 0.05) continue;
      const u = this.sfxUrls[c.name];
      const buf = u ? this.buffers.get(u) : undefined;
      if (!buf) continue;
      const src = this.ctx.createBufferSource();
      const g = this.ctx.createGain();
      g.gain.value = c.gain;
      src.buffer = buf;
      src.connect(g).connect(this.sfxBus);
      src.start(this.t0 + c.at);
      this.track(src);
    }
  }

  /** One-off sound (e.g. the jury's own objection sting). */
  fx(name: Sfx) {
    const u = this.sfxUrls[name];
    const buf = u ? this.buffers.get(u) : undefined;
    if (!buf) return;
    const src = this.ctx.createBufferSource();
    const g = this.ctx.createGain();
    g.gain.value = SFX_GAIN[name];
    src.buffer = buf;
    src.connect(g).connect(this.sfxBus);
    src.start();
    this.track(src);
  }

  private track(src: AudioScheduledSourceNode) {
    this.sources.add(src);
    src.onended = () => this.sources.delete(src);
  }

  stopAll() {
    for (const s of this.sources) {
      try {
        s.onended = null;
        s.stop();
      } catch {
        /* already stopped */
      }
    }
    this.sources.clear();
  }

  position() {
    return this.ctx.currentTime - this.t0;
  }

  async pause() {
    if (this.ctx.state === "running") await this.ctx.suspend();
  }

  async resume() {
    if (this.ctx.state !== "running") await this.ctx.resume();
  }

  setVolume(v: number) {
    this.master.gain.setTargetAtTime(v, this.ctx.currentTime, 0.03);
  }

  /** RMS of the voice bus, 0..~0.5 */
  amplitude = () => {
    this.analyser.getFloatTimeDomainData(this.data);
    let sum = 0;
    for (let i = 0; i < this.data.length; i += 2) sum += this.data[i] * this.data[i];
    return Math.sqrt(sum / (this.data.length / 2));
  };

  dispose() {
    this.stopAll();
    void this.ctx.close();
  }
}
