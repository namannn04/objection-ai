"""Procedural "voice blip" synthesis for MOCK mode.

No network, no model: every character gets a stable pitch/timbre, every word
becomes syllable blips shaped by emotion and intensity, and cue tags become
synthesized breaths, laughs and pauses. Because we render every sample we know
exact word timings, which makes this ideal for testing subtitle sync.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

SR = 24000
_TOKEN = re.compile(r"\[([^\]]+)\]|\*([^*]+)\*|([^\s\[\]*]+)")
_VOWELS = re.compile(r"[aeiouy]+", re.I)


@dataclass(frozen=True, slots=True)
class MockVoice:
    f0: float = 160.0  # base pitch Hz
    speed: float = 6.0  # syllables per second
    brightness: float = 0.5  # 0..1 harmonic richness
    breath: float = 0.05  # noise mix
    wobble: float = 0.02  # pitch variation
    shape: str = "round"  # round | square | reed


EMOTION_MOD: dict[str, tuple[float, float, float, float]] = {
    # emotion: (pitch×, speed×, loudness×, contour range)
    "neutral": (1.0, 1.0, 1.0, 0.10),
    "serious": (0.96, 0.94, 1.0, 0.07),
    "stern": (0.93, 0.92, 1.05, 0.06),
    "angry": (1.08, 1.15, 1.25, 0.16),
    "smug": (1.0, 0.92, 0.95, 0.14),
    "sarcastic": (1.02, 0.95, 0.95, 0.18),
    "desperate": (1.15, 1.2, 1.15, 0.2),
    "shocked": (1.2, 1.1, 1.2, 0.22),
    "confused": (1.05, 0.9, 0.9, 0.18),
    "amused": (1.06, 1.05, 1.0, 0.16),
    "sad": (0.9, 0.8, 0.8, 0.08),
    "proud": (1.0, 0.95, 1.1, 0.12),
    "nervous": (1.1, 1.18, 0.9, 0.15),
    "triumphant": (1.08, 1.0, 1.2, 0.2),
    "deadpan": (0.95, 0.9, 0.9, 0.03),
    "dramatic": (1.02, 0.88, 1.2, 0.24),
    "whispering": (1.0, 0.95, 0.5, 0.06),
    "exasperated": (1.04, 1.05, 1.1, 0.17),
}


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1 if re.search(r"\d", word) else 0
    n = len(_VOWELS.findall(w))
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")):
        n -= 1
    return max(1, min(n, 6))


class _Renderer:
    def __init__(self, voice: MockVoice, emotion: str, intensity: int, seed: int):
        self.v = voice
        pm, sm, lm, contour = EMOTION_MOD.get(emotion, EMOTION_MOD["neutral"])
        k = (intensity - 3) / 2  # -1..1
        self.f0 = voice.f0 * pm * (1 + 0.05 * k)
        self.speed = voice.speed * sm
        self.loud = 0.55 * lm * (1 + 0.15 * k)
        self.contour = contour * (1 + 0.5 * k)
        self.whisper = emotion == "whispering"
        self.rng = np.random.default_rng(seed)
        self.chunks: list[np.ndarray] = []
        self.pos = 0
        self.words: list[dict] = []

    # ── primitives ──────────────────────────────────────────────────────
    def _append(self, x: np.ndarray) -> None:
        self.chunks.append(x.astype(np.float32))
        self.pos += len(x)

    def silence(self, ms: float) -> None:
        self._append(np.zeros(int(SR * ms / 1000)))

    def _env(self, n: int, attack: float = 0.008, release: float = 0.035) -> np.ndarray:
        a, r = max(1, int(SR * attack)), max(1, int(SR * release))
        env = np.ones(n)
        env[: min(a, n)] = np.linspace(0, 1, min(a, n))
        env[-min(r, n) :] *= np.linspace(1, 0, min(r, n))
        return env

    def _tone(self, f: float, dur: float, gain: float, f_end: float | None = None) -> np.ndarray:
        n = max(1, int(SR * dur))
        t = np.arange(n) / SR
        freq = np.linspace(f, f_end or f, n) * (1 + self.v.wobble * np.sin(2 * math.pi * 5.5 * t))
        phase = 2 * math.pi * np.cumsum(freq) / SR
        if self.whisper:
            sig = self.rng.normal(0, 0.35, n) * (0.4 + 0.6 * np.abs(np.sin(phase / 2)))
        else:
            b = self.v.brightness
            if self.v.shape == "square":
                sig = np.sign(np.sin(phase)) * 0.35 + np.sin(phase) * 0.4
            elif self.v.shape == "reed":
                sig = sum((0.9**k) * np.sin(k * phase) for k in range(1, 6)) * 0.3
            else:
                sig = np.sin(phase) + b * 0.45 * np.sin(2 * phase) + b * 0.25 * np.sin(3 * phase)
            sig += self.rng.normal(0, self.v.breath, n)
        return sig * self._env(n) * gain

    def _noise(self, dur: float, gain: float, lo: float = 0.0, sweep: tuple[float, float] = (1.0, 1.0)) -> np.ndarray:
        n = max(1, int(SR * dur))
        x = self.rng.normal(0, 1, n)
        # crude one-pole low-pass whose cutoff sweeps over time
        alpha = np.linspace(sweep[0], sweep[1], n) * 0.25 + lo
        y = np.empty(n)
        acc = 0.0
        for i in range(n):
            acc += alpha[i] * (x[i] - acc)
            y[i] = acc
        return y / (np.max(np.abs(y)) + 1e-9) * gain * self._env(n, 0.03, 0.12)

    # ── speech ──────────────────────────────────────────────────────────
    def word(self, raw: str, emphasis: bool, last_in_clause: bool, question: bool) -> None:
        clean = re.sub(r"[^\w'’-]", "", raw)
        n = syllables(clean)
        start = self.pos
        if n == 0:
            return
        for i in range(n):
            base = self.f0 * (1 + self.contour * self.rng.uniform(-1, 1) * 0.6)
            if emphasis:
                base *= 1.18
            end = base
            if last_in_clause and i == n - 1:
                end = base * (1 + self.contour * 1.8) if question else base * (1 - self.contour * 1.2)
            dur = (1 / self.speed) * self.rng.uniform(0.75, 1.15) * (1.35 if emphasis else 1.0)
            gain = self.loud * (1.3 if emphasis else 1.0) * self.rng.uniform(0.85, 1.0)
            self._append(self._tone(base, dur * 0.82, gain, end))
            self.silence(dur * 0.18 * 1000)
        self.words.append({"w": raw, "s": round(start * 1000 / SR), "e": round(self.pos * 1000 / SR)})

    def punctuation(self, raw: str) -> None:
        if raw.endswith(("...", "…", "—", "-")):
            self.silence(320)
        elif raw.endswith((".", "!", "?")):
            self.silence(300)
        elif raw.endswith((",", ";", ":")):
            self.silence(170)
        else:
            self.silence(55)

    def cue(self, tag: str) -> None:
        tag = tag.strip().lower()
        if tag == "pause":
            self.silence(450)
        elif tag == "long pause":
            self.silence(1100)
        elif tag in ("laugh", "chuckle", "small laugh"):
            reps = 5 if tag == "laugh" else 3
            for i in range(reps):
                f = self.f0 * (1.35 - i * 0.06)
                self._append(self._tone(f, 0.075, self.loud * 0.9) + self._noise(0.075, 0.12))
                self.silence(55)
            self.silence(120)
        elif tag == "sigh":
            self._append(self._noise(0.65, 0.35, 0.02, (1.0, 0.15)))
            self.silence(150)
        elif tag == "gasp":
            self._append(self._noise(0.28, 0.45, 0.05, (0.3, 1.0)))
            self.silence(160)
        elif tag == "clears throat":
            for _ in range(2):
                self._append(self._noise(0.11, 0.4, 0.0, (0.15, 0.1)) + self._tone(self.f0 * 0.6, 0.11, 0.2))
                self.silence(70)
            self.silence(150)
        elif tag in ("scoff", "sobs"):
            self._append(self._noise(0.14 if tag == "scoff" else 0.5, 0.35, 0.03, (0.8, 0.3)))
            self.silence(120)
        elif tag == "whisper":
            self.whisper = True
        else:
            self.silence(200)

    def render(self) -> np.ndarray:
        if not self.chunks:
            return np.zeros(int(SR * 0.2), dtype=np.float32)
        y = np.concatenate(self.chunks)
        peak = float(np.max(np.abs(y))) or 1.0
        return (y / peak * 0.85).astype(np.float32)


def synthesize(text: str, voice: MockVoice, emotion: str = "neutral", intensity: int = 3, seed: int = 0) -> tuple[np.ndarray, list[dict]]:
    """Render a line. Returns (float32 samples at SR, word timings in ms)."""
    r = _Renderer(voice, emotion, intensity, seed)
    r.silence(60)
    tokens = list(_TOKEN.finditer(text))
    words = [(m, i) for i, m in enumerate(tokens) if not m.group(1)]
    for idx, m in enumerate(tokens):
        cue, emph, plain = m.groups()
        if cue:
            r.cue(cue)
            continue
        chunk = emph or plain or ""
        parts = chunk.split() if emph else [chunk]
        for j, part in enumerate(parts):
            last = part.endswith((".", "!", "?", ",", ";", ":", "—", "…")) or (idx == words[-1][1] and j == len(parts) - 1)
            r.word(part, bool(emph), last, part.endswith("?"))
            r.punctuation(part)
    r.silence(120)
    return r.render(), r.words


def to_pcm16(samples: np.ndarray) -> bytes:
    return (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()


# ── sound effects ─────────────────────────────────────────────────────────


def _sfx_renderer(seed: int) -> _Renderer:
    return _Renderer(MockVoice(), "neutral", 3, seed)


def sfx(name: str) -> np.ndarray:
    r = _sfx_renderer(sum(map(ord, name)))
    t = lambda d: np.arange(int(SR * d)) / SR  # noqa: E731
    if name == "gavel":
        out = []
        for k in range(2):
            tt = t(0.22)
            knock = np.sin(2 * math.pi * 180 * tt) * np.exp(-tt * 28) + 0.6 * np.sin(2 * math.pi * 410 * tt) * np.exp(-tt * 45)
            click = r.rng.normal(0, 1, len(tt)) * np.exp(-tt * 140) * 0.5
            out += [knock + click, np.zeros(int(SR * (0.12 if k == 0 else 0.05)))]
        y = np.concatenate(out)
    elif name == "objection":
        tt = t(0.9)
        chord = sum(np.sign(np.sin(2 * math.pi * f * tt)) * 0.25 + np.sin(2 * math.pi * f * tt) * 0.3 for f in (233, 293, 349, 466))
        y = chord * np.minimum(1, tt * 40) * np.exp(-tt * 3.2)
    elif name == "dramatic_sting":
        tt = t(1.6)
        y = sum(np.sin(2 * math.pi * f * tt * (1 - 0.04 * tt)) for f in (110, 131, 165, 220)) * np.minimum(1, tt * 25) * np.exp(-tt * 1.6)
        y += r.rng.normal(0, 0.15, len(tt)) * np.exp(-tt * 6)
    elif name == "crowd_gasp":
        y = sum(_crowd_voice(r, 0.6, k, rise=True) for k in range(9))
    elif name == "crowd_laugh":
        y = sum(_crowd_laugh(r, k) for k in range(8))
    elif name == "crowd_murmur":
        y = r._noise(1.6, 0.6, 0.01, (0.25, 0.2)) * (0.6 + 0.4 * np.sin(2 * math.pi * 3.1 * t(1.6)))
    else:
        y = np.zeros(int(SR * 0.3))
    y = np.asarray(y, dtype=np.float64)
    return (y / (np.max(np.abs(y)) + 1e-9) * 0.8).astype(np.float32)


def _crowd_voice(r: _Renderer, dur: float, k: int, rise: bool) -> np.ndarray:
    n = int(SR * dur)
    off = int(r.rng.uniform(0, 0.12) * SR)
    x = np.zeros(n)
    seg = r._noise(dur - off / SR, r.rng.uniform(0.3, 0.6), 0.03, (0.2, 1.0) if rise else (1.0, 0.2))
    x[off : off + len(seg)] = seg[: n - off]
    return x


def _crowd_laugh(r: _Renderer, k: int) -> np.ndarray:
    total = int(SR * 1.8)
    x = np.zeros(total)
    f0 = r.rng.uniform(140, 320)
    pos = int(r.rng.uniform(0, 0.25) * SR)
    for i in range(int(r.rng.integers(4, 8))):
        tt = np.arange(int(SR * 0.09)) / SR
        ha = np.sin(2 * math.pi * f0 * (1 - 0.1 * i / 8) * tt) * np.sin(math.pi * tt / 0.09) * 0.3
        ha += r.rng.normal(0, 0.12, len(tt)) * np.sin(math.pi * tt / 0.09)
        if pos + len(ha) >= total:
            break
        x[pos : pos + len(ha)] += ha * (1 - i / 10)
        pos += int(SR * r.rng.uniform(0.12, 0.18))
    return x
