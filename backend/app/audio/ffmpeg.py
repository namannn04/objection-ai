"""FFmpeg/FFprobe helpers. Uses system binaries when present, else the binary
bundled with imageio-ffmpeg (no ffprobe there, so duration falls back to
parsing `ffmpeg -i`)."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache
def ffmpeg_bin() -> str:
    sysbin = shutil.which("ffmpeg")
    if sysbin:
        return sysbin
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


@lru_cache
def ffprobe_bin() -> str | None:
    return shutil.which("ffprobe")


def _run(args: list[str], data: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, input=data, capture_output=True, check=False)


def encode_pcm(pcm16: bytes, sample_rate: int, out: Path, fmt: str = "mp3", bitrate: str = "96k") -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    codec = ["-codec:a", "libmp3lame", "-b:a", bitrate] if fmt == "mp3" else ["-codec:a", "pcm_s16le"]
    p = _run([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(sample_rate),
              "-ac", "1", "-i", "pipe:0", *codec, str(out)], pcm16)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg encode failed: {p.stderr.decode()[-400:]}")


_DUR = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def probe_duration_ms(path: Path) -> int:
    """Actual media duration. Never estimated from text."""
    probe = ffprobe_bin()
    if probe:
        p = _run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
        if p.returncode == 0:
            try:
                return round(float(json.loads(p.stdout)["format"]["duration"]) * 1000)
            except (KeyError, ValueError):
                pass
    # Decode fully so the duration is exact even for VBR files.
    p = _run([ffmpeg_bin(), "-hide_banner", "-i", str(path), "-f", "null", "-"])
    times = re.findall(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", p.stderr.decode())
    if times:
        h, m, s = times[-1]
        return round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)
    m = _DUR.search(p.stderr.decode())
    if not m:
        raise RuntimeError(f"could not probe duration of {path}")
    return round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * 1000)


def detect_silences(path: Path, noise_db: int = -35, min_s: float = 0.25) -> list[tuple[int, int]]:
    """Silence intervals (ms) — used to split multi-speaker scene audio into turns."""
    p = _run([ffmpeg_bin(), "-hide_banner", "-i", str(path), "-af",
              f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"])
    err = p.stderr.decode()
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return [(round(s * 1000), round(e * 1000)) for s, e in zip(starts, ends, strict=False)]


def cut(src: Path, out: Path, start_ms: int, end_ms: int) -> None:
    p = _run([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-ss", f"{start_ms / 1000:.3f}",
              "-to", f"{end_ms / 1000:.3f}", "-codec:a", "libmp3lame", "-b:a", "128k", str(out)])
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[-300:])


async def mix_timeline(items: list[tuple[Path, int, float]], out: Path, total_ms: int, fmt: str) -> None:
    """Mix audio files placed at absolute offsets (ms) with gains into one file."""
    out.parent.mkdir(parents=True, exist_ok=True)
    args = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y"]
    filters = []
    for i, (path, _, _) in enumerate(items):
        args += ["-i", str(path)]
    for i, (_, offset, gain) in enumerate(items):
        filters.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,adelay={offset}:all=1,volume={gain}[a{i}]")
    labels = "".join(f"[a{i}]" for i in range(len(items)))
    filters.append(f"{labels}amix=inputs={len(items)}:normalize=0:dropout_transition=0,apad=whole_dur={total_ms / 1000:.3f},"
                   f"atrim=0:{total_ms / 1000:.3f},alimiter=limit=0.95[out]")
    codec = ["-codec:a", "libmp3lame", "-b:a", "160k"] if fmt == "mp3" else ["-codec:a", "pcm_s16le"]
    script = out.with_suffix(".filter.txt")
    script.write_text(";\n".join(filters))
    args += ["-filter_complex_script", str(script), "-map", "[out]", "-ac", "1", *codec, str(out)]
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    script.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed: {err.decode()[-600:]}")
