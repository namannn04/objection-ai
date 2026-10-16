"""Natural pacing and caption alignment for recorded lines.

TTS models leave long dead air around [pause] cues and slow deliveries, which
makes a trial feel sluggish. `tighten` shortens only the silences (speech is
never time-stretched, so voices keep their pitch and texture). `align_words`
then places each caption word on the speech the listener actually hears,
using the voiced regions of the final audio.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np

from app.audio.ffmpeg import encode_pcm, ffmpeg_bin
from app.audio.mock_synth import syllables

SR = 44100
HOP = SR // 100  # 10 ms analysis frames

LEAD_MS, TAIL_MS = 60, 140  # silence kept before the first / after the last sound
KEEP_MS = 170  # gaps up to this length are natural breaths: untouched
MAX_GAP_MS = 400  # even a [long pause] never leaves more dead air than this
SQUEEZE = 0.25  # share of the gap beyond KEEP_MS that survives
FADE = SR // 200  # 5 ms fades at every cut: no clicks


def decode(path: Path) -> np.ndarray:
    p = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=False)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(f"could not decode {path}: {p.stderr.decode()[-200:]}")
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768


def voiced_segments(x: np.ndarray, min_gap_ms: int = 120) -> list[tuple[int, int]]:
    """Voiced regions in ms. Threshold is relative to the line's own loudness."""
    n = len(x) // HOP
    if n == 0:
        return []
    db = 10 * np.log10((x[: n * HOP].reshape(n, HOP) ** 2).mean(1) + 1e-10)
    thr = max(np.percentile(db, 95) - 34, np.percentile(db, 10) + 8, -60)
    v = db > thr
    segs: list[list[int]] = []
    i = 0
    while i < n:
        if v[i]:
            j = i
            while j < n and v[j]:
                j += 1
            if segs and i * 10 - segs[-1][1] < min_gap_ms:
                segs[-1][1] = j * 10  # a tiny dip inside a word is not a pause
            else:
                segs.append([i * 10, j * 10])
            i = j
        else:
            i += 1
    return [(s, e) for s, e in segs if e - s >= 40]


def _target_gap(gap: int) -> int:
    if gap <= KEEP_MS:
        return gap
    return min(MAX_GAP_MS, round(KEEP_MS + (gap - KEEP_MS) * SQUEEZE))


def tighten(x: np.ndarray) -> np.ndarray:
    """Shorten leading/trailing/inner silences; speech samples are copied untouched."""
    segs = voiced_segments(x)
    if not segs:
        return x
    ms = SR // 1000
    pieces: list[np.ndarray] = []

    def take(a_ms: int, b_ms: int) -> None:
        a, b = max(0, a_ms * ms), min(len(x), b_ms * ms)
        if b > a:
            pieces.append(x[a:b].copy())

    def quiet(n_ms: int, at_ms: int) -> None:
        # Room tone from the gap itself (not digital silence), faded at both ends.
        a = max(0, at_ms * ms)
        chunk = x[a : a + n_ms * ms].copy()
        if len(chunk) < n_ms * ms:
            chunk = np.zeros(n_ms * ms, dtype=np.float32)
        f = min(FADE, len(chunk) // 2)
        if f:
            chunk[:f] *= np.linspace(0, 1, f)
            chunk[-f:] *= np.linspace(1, 0, f)
        pieces.append(chunk)

    first_s = segs[0][0]
    take(max(0, first_s - LEAD_MS), first_s)
    for k, (s, e) in enumerate(segs):
        take(s, e)
        if k + 1 < len(segs):
            nxt = segs[k + 1][0]
            gap = nxt - e
            want = _target_gap(gap)
            if want == gap:
                take(e, nxt)
            else:
                # Keep the soft edges of the gap (tails of words, breaths), drop the middle.
                edge = min(want // 2, 90)
                take(e, e + edge)
                quiet(max(0, want - 2 * edge), e + edge)
                take(nxt - edge, nxt)
    last_e = segs[-1][1]
    take(last_e, last_e + TAIL_MS)
    y = np.concatenate(pieces) if pieces else x
    f = min(FADE * 4, len(y) // 4)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def tighten_file(src: Path, out: Path, bitrate: str = "128k") -> np.ndarray:
    """Write a tightened copy of `src` to `out`; returns the tightened samples."""
    y = tighten(decode(src))
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    encode_pcm(pcm, SR, out, "mp3", bitrate)
    return y


def caption_timings(text: str, y: np.ndarray) -> tuple[list[dict], str]:
    """Caption word timings for the final audio, placed on its measured speech regions."""
    segs = voiced_segments(y)
    duration = round(len(y) / SR * 1000)
    words = align_words(text, segs, duration)
    return words, "aligned"


# ---- caption alignment -------------------------------------------------------

_BRACKET = re.compile(r"(\[[^\]]+\])")
_SOUNDS = {"laugh": 2.5, "laughs": 2.5, "chuckle": 1.6, "chuckles": 1.6, "sigh": 1.8, "sighs": 1.8, "gasp": 1.0,
           "gasps": 1.0, "inhales": 0.8, "inhale": 0.8, "clears throat": 1.6, "groans": 1.4, "groan": 1.4,
           "sniff": 0.6, "scoff": 0.8, "scoffs": 0.8, "giggle": 1.6, "giggles": 1.6, "yawn": 2.0, "yawns": 2.0}
_PAUSES = {"pause", "long pause", "short pause", "beat"}


def _tokens(text: str) -> list[tuple[str | None, float, bool]]:
    """(word or None for a sound, voiced weight, a pause may follow)."""
    text = re.sub(r"<\|?[^<>]*\|?>", "", text)  # provider markup (<emphasis>, <|speaker:N|>) is never shown
    out: list[tuple[str | None, float, bool]] = []
    for part in _BRACKET.split(text):
        part = part.strip()
        if not part:
            continue
        if part.startswith("[") and part.endswith("]"):
            cue = part[1:-1].strip().lower()
            if cue in _SOUNDS:
                out.append((None, _SOUNDS[cue], True))
            elif cue in _PAUSES and out:
                out[-1] = (out[-1][0], out[-1][1], True)
            continue  # stage directions are not spoken
        for w in part.replace("*", "").split():
            out.append((w, max(1, syllables(w)) + 0.3, bool(re.search(r"[.!?,;:—…]['\"”’)]*$", w))))
    return out


def align_words(text: str, segs: list[tuple[int, int]], duration_ms: int) -> list[dict]:
    """Word timings on the measured speech. Words advance only while someone is talking,
    and the clear pauses are matched to sentence/comma boundaries with a global search
    that keeps the speaking rate as even as possible across the line."""
    toks = _tokens(text)
    if not toks:
        return []
    if not segs:
        segs = [(min(120, duration_ms // 4), max(duration_ms - 150, duration_ms // 2))]
    cum = np.concatenate([[0.0], np.cumsum([t[1] for t in toks])])
    total_w = float(cum[-1]) or 1.0
    vcum = np.concatenate([[0], np.cumsum([e - s for s, e in segs])])
    total_v = float(vcum[-1]) or 1.0
    rate = total_w / total_v

    # Candidate cuts: gaps after segment k (≥150 ms) ↔ token boundaries where a pause may fall.
    gaps = [k + 1 for k in range(len(segs) - 1) if segs[k + 1][0] - segs[k][1] >= 150]
    bounds = [i + 1 for i, t in enumerate(toks[:-1]) if t[2]]
    gap_ms = {k: segs[k][0] - segs[k - 1][1] for k in gaps}
    G = [0, *gaps, len(segs)]  # segment indices where a chunk starts
    B = [0, *bounds, len(toks)]

    def chunk_cost(g0: int, g1: int, b0: int, b1: int) -> float:
        w, v = cum[B[b1]] - cum[B[b0]], vcum[G[g1]] - vcum[G[g0]]
        skipped = sum(min(gap_ms[G[g]], 900) for g in range(g0 + 1, g1)) / 1000
        return float(np.log((w + 0.3) / (v * rate + 0.3)) ** 2 * (w / total_w + v / total_v)) + 0.06 * skipped

    inf = float("inf")
    nG, nB = len(G), len(B)
    dp = np.full((nG, nB), inf)
    back: dict[tuple[int, int], tuple[int, int]] = {}
    dp[0][0] = 0.0
    for g1 in range(1, nG):
        for b1 in range(1, nB):
            if (g1 == nG - 1) != (b1 == nB - 1):
                continue  # the last chunk ends exactly at the last token and the last segment
            best, arg = inf, None
            for g0 in range(g1):
                for b0 in range(b1):
                    if dp[g0][b0] == inf:
                        continue
                    c = dp[g0][b0] + chunk_cost(g0, g1, b0, b1)
                    if c < best:
                        best, arg = c, (g0, b0)
            if arg:
                dp[g1][b1], back[(g1, b1)] = best, arg
    path = [(nG - 1, nB - 1)]
    while path[-1] != (0, 0) and path[-1] in back:
        path.append(back[path[-1]])
    path.reverse()

    out: list[dict] = []
    for (g0, b0), (g1, b1) in zip(path, path[1:], strict=False):
        span = segs[G[g0] : G[g1]]
        t0, t1 = B[b0], B[b1]
        span_v = sum(e - s for s, e in span) or 1
        w0, w_span = cum[t0], (cum[t1] - cum[t0]) or 1

        def at(wpos: float, span=span, span_v=span_v, w0=w0, w_span=w_span) -> float:
            target = (wpos - w0) / w_span * span_v
            for s, e in span:
                if target <= e - s:
                    return s + target
                target -= e - s
            return span[-1][1]

        for i in range(t0, t1):
            if toks[i][0]:
                s, e = at(cum[i]), at(cum[i + 1])
                out.append({"w": toks[i][0], "s": round(s), "e": round(max(s + 60, e))})
    return out
