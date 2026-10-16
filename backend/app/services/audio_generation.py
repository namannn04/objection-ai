"""AudioGenerationService: turns dialogue rows into audio assets.

Per turn: compile → cache lookup → budget guard → synthesize → validate →
save → ffprobe duration → timings → link. Failures never corrupt the case:
a turn without audio is reported, and the job ends `blocked` or `failed`.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio import ffmpeg, mock_synth
from app.audio.budget import BudgetGuard, estimate_cost, record
from app.audio.compiler import CompiledRequest, compile_line
from app.audio.mock_synth import MockVoice, syllables
from app.audio.providers import AudioProvider, ProviderError, get_audio_provider
from app.config import get_settings
from app.domain.models import DialogueTurn
from app.models import AudioAsset, Case, DialogueTurnRow, VoiceAssignment

Progress = Callable[[str, dict], Awaitable[None]]

_ENSEMBLE_PACE = {"judge": "slow", "prosecutor": "fast", "defense": "measured", "reporter": "measured"}
_MOCK_FIELDS = {"f0", "speed", "brightness", "breath", "wobble", "shape"}

SFX_NAMES = ("gavel", "objection", "crowd_gasp", "crowd_laugh", "crowd_murmur", "dramatic_sting")
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "audio" / "fixtures" / "sfx"


async def _noop(_: str, __: dict) -> None:
    return None


def asset_path(cache_key: str, fmt: str = "mp3") -> Path:
    return get_settings().audio_dir / cache_key[:2] / f"{cache_key}.{fmt}"


def asset_url(asset: AudioAsset) -> str:
    return f"/media/audio/{asset.cache_key[:2]}/{asset.cache_key}.{asset.format}"


def ensure_sfx_fixtures() -> dict[str, Path]:
    """Prerecorded SFX fixtures (synthesized once, committed to the repo)."""
    out = {}
    for name in SFX_NAMES:
        path = FIXTURE_DIR / f"{name}.mp3"
        if not path.exists():
            ffmpeg.encode_pcm(mock_synth.to_pcm16(mock_synth.sfx(name)), mock_synth.SR, path, bitrate="96k")
        out[name] = path
    return out


_CUE = re.compile(r"\[([^\]]+)\]")
_CUE_WEIGHT = {"pause": 2.6, "long pause": 6.0, "laugh": 3.0, "sigh": 3.0, "gasp": 1.8, "clears throat": 2.2}


def estimate_word_timings(text: str, duration_ms: int) -> list[dict]:
    """Distribute words across the *measured* duration by syllable weight.
    Used only when the provider does not return alignment."""
    tokens: list[tuple[str | None, float]] = []
    text = re.sub(r"<\|?[^<>]*\|?>", "", text)  # provider markup (<emphasis>, <|speaker:0|>) is never shown
    for part in re.split(r"(\[[^\]]+\])", text):
        m = _CUE.fullmatch(part.strip()) if part.strip() else None
        if m:
            tokens.append((None, _CUE_WEIGHT.get(m.group(1).lower(), 1.0)))
            continue
        for w in part.replace("*", "").split():
            weight = max(1, syllables(w)) + (1.6 if w.endswith((".", "!", "?")) else 0.8 if w.endswith((",", ";", ":", "—")) else 0.25)
            tokens.append((w, weight))
    total = sum(wt for _, wt in tokens) or 1
    lead, tail = 120, 150
    span = max(1, duration_ms - lead - tail)
    pos, out = float(lead), []
    for w, wt in tokens:
        dur = span * wt / total
        if w:
            out.append({"w": w, "s": round(pos), "e": round(pos + dur * 0.85)})
        pos += dur
    return out


@dataclass(slots=True)
class PrepReport:
    total: int = 0
    cached: int = 0
    synthesized: int = 0
    blocked: int = 0
    failed: int = 0
    characters: int = 0
    estimated_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.blocked == 0 and self.failed == 0


class AudioGenerationService:
    def __init__(self, provider: AudioProvider | None = None):
        self.settings = get_settings()
        self.provider = provider or get_audio_provider(self.settings)
        self.guard = BudgetGuard(self.settings)

    async def _voices(self, session: AsyncSession, case: Case) -> dict[str, VoiceAssignment]:
        return {c.key: c.voice for c in case.characters if c.voice}

    def compile(self, row: DialogueTurnRow, voice: VoiceAssignment) -> CompiledRequest:
        turn = DialogueTurn.model_validate(row.data)
        pace = (voice.mock_params or {}).get("pace") or _ENSEMBLE_PACE.get(row.speaker, "measured")
        return compile_line(self.provider.name, self.provider.model, turn, voice.voice_id, voice.base_direction,
                            mock_seed=voice.voice_id + voice.base_direction, pace=pace)

    async def estimate(self, session: AsyncSession, case: Case, rows: list[DialogueTurnRow]) -> PrepReport:
        voices = await self._voices(session, case)
        rep = PrepReport()
        for row in rows:
            req = self.compile(row, voices[row.speaker])
            rep.total += 1
            if await self._cached(session, req.cache_key):
                rep.cached += 1
                continue
            rep.characters += req.characters
            rep.estimated_cost_usd += estimate_cost(self.settings, req.provider, req.characters)
        rep.estimated_cost_usd = round(rep.estimated_cost_usd, 4)
        return rep

    async def _cached(self, session: AsyncSession, key: str) -> AudioAsset | None:
        asset = (await session.execute(select(AudioAsset).where(AudioAsset.cache_key == key))).scalar_one_or_none()
        if asset and Path(asset.path).exists():
            return asset
        return None

    async def prepare(self, session: AsyncSession, case: Case, rows: list[DialogueTurnRow], progress: Progress = _noop,
                      *, allow_reserve: bool = False) -> PrepReport:
        """Three passes so the single DB session is never used concurrently:
        1) serial: cache lookups + budget check of the *whole* pending batch,
        2) concurrent: provider synthesis + encode + probe (no DB),
        3) serial: persist assets, link turns, write the audit log."""
        voices = await self._voices(session, case)
        rep = PrepReport(total=len(rows))
        billable = self.provider.billable
        if self.provider.name == "drama3" and self.settings.drama3_scene_strategy:
            rows = await self._prepare_scene_blocks(session, case, rows, voices, rep, progress, allow_reserve)
            if rep.blocked or rep.failed:
                await session.flush()
                return rep
        pending: list[tuple[DialogueTurnRow, VoiceAssignment, CompiledRequest]] = []
        seen: dict[str, AudioAsset | None] = {}
        for row in rows:
            voice = voices[row.speaker]
            req = self.compile(row, voice)
            asset = await self._cached(session, req.cache_key)
            if asset:
                row.audio_asset_id = asset.id
                rep.cached += 1
                await record(session, case_id=case.id, req=req, outcome="cache_hit", cost=0, billable=billable)
            elif req.cache_key in seen:
                pending.append((row, voice, req))  # identical line twice: synthesize once, link both
            else:
                seen[req.cache_key] = None
                pending.append((row, voice, req))
        await progress("audio", {"done": rep.cached, "total": rep.total, "cached": rep.cached, "synthesized": 0})

        unique = list({req.cache_key: (row, voice, req) for row, voice, req in pending}.values())
        if billable and unique:
            planned_chars = 0
            planned_cost = 0.0
            for _, _, req in unique:
                d = await self.guard.check(session, case, req, billable=True, allow_reserve=allow_reserve,
                                           extra_chars=planned_chars, extra_cost=planned_cost)
                if not d.allowed:
                    rep.blocked = len(pending)
                    rep.errors.append(d.reason)
                    await record(session, case_id=case.id, req=req, outcome="blocked", cost=d.cost_usd,
                                 billable=True, detail=d.code)
                    await session.flush()
                    return rep
                planned_chars += req.characters
                planned_cost += d.cost_usd

        sem = asyncio.Semaphore(6 if self.provider.name == "mock" else 3)  # Fish: max 5 concurrent per account
        stop = asyncio.Event()
        done = rep.cached

        async def run(row: DialogueTurnRow, voice: VoiceAssignment, req: CompiledRequest):
            nonlocal done
            async with sem:
                if stop.is_set():
                    return req, None, ProviderError("skipped after an earlier failure")
                if not await self.guard.acquire(req.cache_key):
                    return req, None, ProviderError("identical request already in flight")
                try:
                    out = await self._render(req, voice)
                    done += 1
                    await progress("audio", {"done": done, "total": rep.total, "turn": row.turn_key,
                                             "cached": rep.cached, "synthesized": done - rep.cached})
                    return req, out, None
                except ProviderError as exc:
                    stop.set()  # no partial surprise spending after a failure
                    return req, None, exc
                finally:
                    await self.guard.release(req.cache_key)

        results = await asyncio.gather(*(run(*u) for u in unique))
        assets: dict[str, AudioAsset] = {}
        for (row, voice, _), (req, out, err) in zip(unique, results, strict=True):
            cost = estimate_cost(self.settings, req.provider, req.characters)
            if err is not None:
                skipped = str(err).startswith(("skipped", "identical"))
                rep.blocked += skipped
                rep.failed += not skipped
                rep.errors.append(str(err))
                if not skipped:
                    await record(session, case_id=case.id, req=req, outcome="uncertain" if err.uncertain else "failed",
                                 cost=cost, billable=billable, detail=str(err))
                continue
            path, duration, timings, source = out
            asset = AudioAsset(cache_key=req.cache_key, provider=self.provider.name, model=self.provider.model,
                               path=str(path), format="mp3", duration_ms=duration, size_bytes=path.stat().st_size,
                               characters=req.characters, timings={"words": timings, "source": source},
                               meta={"voice": voice.voice_label, "turn": row.turn_key})
            session.add(asset)
            assets[req.cache_key] = asset
            rep.synthesized += 1
            rep.characters += req.characters
            rep.estimated_cost_usd += cost if billable else 0.0
            await record(session, case_id=case.id, req=req, outcome="synthesized", cost=cost, billable=billable)
        await session.flush()
        for row, _, req in pending:
            if req.cache_key in assets:
                row.audio_asset_id = assets[req.cache_key].id
        await session.flush()
        rep.estimated_cost_usd = round(rep.estimated_cost_usd, 4)
        return rep

    async def _prepare_scene_blocks(self, session, case, rows, voices, rep: PrepReport, progress, allow_reserve) -> list:
        """Main-branch scenes go out as one multi-speaker request each; returns rows left for line mode."""
        from app.audio.compiler import compile_scene
        from app.audio.scene_split import split_scene

        by_scene: dict[str, list[DialogueTurnRow]] = {}
        rest = []
        for r in rows:
            (by_scene.setdefault(r.scene_id, []) if r.branch_key is None and r.session_id is None else rest).append(r)
        for scene_rows in by_scene.values():
            scene_rows.sort(key=lambda r: r.order)
            if len(scene_rows) < 2:
                rest.extend(scene_rows)
                continue
            turns = [DialogueTurn.model_validate(r.data) for r in scene_rows]
            req = compile_scene(self.provider.model, turns,
                                {r.speaker: (voices[r.speaker].voice_id, voices[r.speaker].base_direction) for r in scene_rows})
            keys = [hashlib.sha256(f"{req.cache_key}:{i}".encode()).hexdigest() for i in range(len(scene_rows))]
            cached = [await self._cached(session, k) for k in keys]
            if all(cached):
                for r, a in zip(scene_rows, cached, strict=True):
                    r.audio_asset_id = a.id
                rep.cached += len(scene_rows)
                continue
            d = await self.guard.check(session, case, req, billable=True, allow_reserve=allow_reserve)
            if not d.allowed:
                rep.blocked += len(scene_rows)
                rep.errors.append(d.reason)
                await record(session, case_id=case.id, req=req, outcome="blocked", cost=d.cost_usd, billable=True, detail=d.code)
                return rest
            cost = estimate_cost(self.settings, req.provider, req.characters)
            try:
                result = await self.provider.synthesize(req, None)
            except ProviderError as exc:
                rep.failed += len(scene_rows)
                rep.errors.append(str(exc))
                await record(session, case_id=case.id, req=req, outcome="uncertain" if exc.uncertain else "failed",
                             cost=cost, billable=True, detail=str(exc))
                return rest
            full = asset_path(req.cache_key)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(result.audio)
            await record(session, case_id=case.id, req=req, outcome="synthesized", cost=cost, billable=True,
                         detail=f"scene block of {len(scene_rows)} lines")
            outs = [asset_path(k) for k in keys]
            pieces, method = await asyncio.to_thread(split_scene, full, outs, [len(t.text) for t in turns])
            for r, k, t, (path, dur) in zip(scene_rows, keys, turns, pieces, strict=True):
                a = AudioAsset(cache_key=k, provider=self.provider.name, model=self.provider.model, path=str(path),
                               format="mp3", duration_ms=dur, size_bytes=path.stat().st_size, characters=len(t.text),
                               timings={"words": estimate_word_timings(t.text, dur), "source": "estimated"},
                               meta={"strategy": "scene", "split": method, "scene_request": req.cache_key})
                session.add(a)
                await session.flush()
                r.audio_asset_id = a.id
            rep.synthesized += len(scene_rows)
            rep.characters += req.characters
            rep.estimated_cost_usd += cost
            await progress("audio", {"done": rep.cached + rep.synthesized, "total": rep.total})
        return rest

    async def _render(self, req: CompiledRequest, voice: VoiceAssignment) -> tuple[Path, int, list[dict], str]:
        billable = self.provider.billable
        mv = MockVoice(**{k: v for k, v in voice.mock_params.items() if k in _MOCK_FIELDS}) if voice.mock_params else None
        attempts = 0
        while True:
            attempts += 1
            try:
                result = await self.provider.synthesize(req, mv)
                break
            except ProviderError as exc:
                # Retry only when the request provably never billed (connect error / 429 / 503).
                if exc.retryable and attempts < 3:
                    await asyncio.sleep(1.5 * 2**attempts)
                    continue
                raise
        path = asset_path(req.cache_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if result.pcm:
                await asyncio.to_thread(ffmpeg.encode_pcm, result.audio, result.sample_rate, path, "mp3", "96k")
            else:
                path.write_bytes(result.audio)
            duration = await asyncio.to_thread(ffmpeg.probe_duration_ms, path)
        except RuntimeError as exc:
            raise ProviderError(f"returned audio is not decodable: {exc}", uncertain=billable) from exc
        if duration < 150:
            raise ProviderError(f"audio too short ({duration} ms)", uncertain=billable)
        if result.word_timings:
            timings = [{**w, "e": min(w["e"], duration)} for w in result.word_timings]
            return path, duration, timings, result.timing_source
        return path, duration, estimate_word_timings(req.text, duration), "estimated"
