"""Split one multi-speaker scene recording into per-line clips.

Drama 3 can perform a whole exchange in one request (better continuity), but
the player needs per-line audio for subtitles, reactions and seeking. We cut at
the N-1 longest silences; if the recording doesn't have enough clean gaps we
fall back to proportional cuts by text length — never a second, billed request.
"""

from __future__ import annotations

from pathlib import Path

from app.audio import ffmpeg


def cut_points(silences: list[tuple[int, int]], n_lines: int, duration_ms: int, weights: list[int]) -> tuple[list[int], str]:
    """Return n_lines-1 cut positions (ms) and the method used."""
    need = n_lines - 1
    if need <= 0:
        return [], "single"
    inner = [(s, e) for s, e in silences if s > 150 and e < duration_ms - 150]
    if len(inner) >= need:
        longest = sorted(inner, key=lambda se: se[1] - se[0], reverse=True)[:need]
        cuts = sorted((s + e) // 2 for s, e in longest)
        # Sanity: each piece should be roughly proportional to its text (within 4x).
        bounds = [0, *cuts, duration_ms]
        total_w = sum(weights) or 1
        ok = all(
            (b - a) > 250 and 0.25 < ((b - a) / duration_ms) / (w / total_w) < 4
            for (a, b), w in zip(zip(bounds, bounds[1:]), weights, strict=True)
        )
        if ok:
            return cuts, "silence"
    total_w = sum(weights) or 1
    acc, cuts = 0, []
    for w in weights[:-1]:
        acc += w
        cuts.append(round(duration_ms * acc / total_w))
    return cuts, "proportional"


def split_scene(src: Path, out_paths: list[Path], weights: list[int]) -> tuple[list[tuple[Path, int]], str]:
    duration = ffmpeg.probe_duration_ms(src)
    cuts, method = cut_points(ffmpeg.detect_silences(src), len(out_paths), duration, weights)
    bounds = [0, *cuts, duration]
    pieces = []
    for path, (a, b) in zip(out_paths, zip(bounds, bounds[1:]), strict=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg.cut(src, path, a, b)
        pieces.append((path, ffmpeg.probe_duration_ms(path)))
    return pieces, method
