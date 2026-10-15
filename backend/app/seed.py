"""Seed the showcase case and curated "Case of the Day" trials (idempotent).

    python -m app.seed            # showcase + curated cases, mock audio
    python -m app.seed --showcase # showcase only
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.db import session_factory
from app.domain.models import Phase
from app.domain.validation import validate_script
from app.models import Case
from app.services import case_service as cs
from app.services.pipeline import _synthesize, all_rows, prepare_case
from app.services.settings_service import provider_status
from app.showcase import javascript

log = logging.getLogger("seed")

CURATED = [
    {"defendant": "The office Wi-Fi", "accusation": "disappearing during every important meeting", "trial_length": "quick"},
    {"defendant": "Monday mornings", "accusation": "crimes against humanity, fifty-two times a year", "trial_length": "quick"},
    {"defendant": "My alarm clock", "accusation": "destroying my dreams every single morning", "trial_length": "quick"},
    {"defendant": "My friend who is always five minutes away", "accusation": "saying 'I'm on my way' from the shower", "trial_length": "quick"},
]


async def _noop(*_):
    return None


async def best_free_voice() -> str:
    """Real voices whenever possible: Fish S2.1 Pro Free once verified, mock only as a last resort."""
    async with session_factory()() as s:
        status = await provider_status(s)
    return "fish-free" if status["audio"]["fish-free"]["available"] else "mock"


async def seed_showcase() -> str:
    async with session_factory()() as s:
        case = (await s.execute(select(Case).where(Case.slug == javascript.CASE_FIELDS["slug"]))).scalar_one_or_none()
        if case and case.status == Phase.COURTROOM_READY.value:
            cv = await cs.current_version(s, case)
            if cv and cv.script == javascript.SCRIPT.model_dump(mode="json"):
                log.info("showcase already present: %s", case.slug)
                return case.id
            log.info("showcase script changed; re-syncing %s", case.slug)
            cs.advance(case, Phase.AUDIO_PREPARATION)
        report = validate_script(javascript.PLAN, javascript.SCRIPT)
        if not report.valid:
            raise SystemExit(f"showcase script invalid: {report.errors}")
        if not case:
            f = javascript.CASE_FIELDS
            case = Case(slug=f["slug"], defendant=f["defendant"], accusation=f["accusation"], context=f["context"],
                        comedy_intensity=f["comedy_intensity"], drama_level=f["drama_level"], trial_length=f["trial_length"],
                        participation_mode=f["participation_mode"], case_number=f["case_number"], is_showcase=True,
                        is_featured=True, llm_provider="hand-authored", audio_provider=await best_free_voice(),
                        status=Phase.CASE_CREATED.value)
            s.add(case)
            await s.flush()
        for target in (Phase.CASE_PREPARATION, Phase.SCRIPT_PLANNING, Phase.SCRIPT_VALIDATION):
            if case.status != target.value and Phase(case.status) != Phase.AUDIO_PREPARATION:
                cs.advance(case, target)
        await cs.save_trial(s, case, javascript.PLAN, javascript.SCRIPT, humor=[], validation=report.model_dump(),
                            generator="hand-authored")
        if case.status == Phase.SCRIPT_VALIDATION.value:
            cs.advance(case, Phase.AUDIO_PREPARATION, script_valid=True)
        await s.commit()
        case = await cs.load_case(s, case.id)
        out = await _synthesize(s, case, _noop, await best_free_voice())
        log.info("showcase audio: %s", {k: out[k] for k in ("total", "synthesized", "cached")})
        return case.id


async def seed_curated() -> None:
    from app.models import AudioGenerationJob

    for spec in CURATED:
        async with session_factory()() as s:
            exists = (await s.execute(select(Case).where(Case.defendant == spec["defendant"], Case.is_featured.is_(True)))).scalar_one_or_none()
            if exists:
                continue
            voice = await best_free_voice()
            case = await cs.create_case(s, {**spec, "participation_mode": "jury", "drama_level": 65}, "mock", voice)
            case.is_featured = True
            job = AudioGenerationJob(kind="prepare_case", case_id=case.id, status="running")
            s.add(job)
            await s.commit()
            await prepare_case(s, job, _noop)
            job.status = "done"
            await s.commit()
            log.info("curated case ready: %s", case.slug)


async def revoice() -> None:
    """Re-record every case that still has placeholder (mock) voices with real free voices.
    Unchanged lines come from the cache, so this is quick after the first run."""
    voice = await best_free_voice()
    if voice == "mock":
        log.info("real voices not available (verify S2.1 Pro Free in Settings); skipping re-voice")
        return
    async with session_factory()() as s:
        ids = [c.id for c in (await s.execute(select(Case).where(
            Case.status.in_([Phase.COURTROOM_READY.value, Phase.AUDIO_PREPARATION.value])))).scalars()]
    for case_id in ids:
        async with session_factory()() as s:
            case = await cs.load_case(s, case_id)
            if not case or not case.scenes:
                continue
            rows = await all_rows(s, case)
            if rows and all(r.audio and r.audio.provider != "mock" for r in rows):
                continue
            if case.status == Phase.COURTROOM_READY.value:
                cs.advance(case, Phase.AUDIO_PREPARATION)
            case.audio_provider = voice
            await s.commit()
            case = await cs.load_case(s, case_id)
            out = await _synthesize(s, case, _noop, voice)
            log.info("re-voiced %s with %s: %s", case.slug, voice,
                     {k: out[k] for k in ("synthesized", "cached", "blocked", "failed")})


async def recast_all() -> None:
    """Re-cast every case with the current voice casting (voices + pace), then re-record with real voices."""
    from app.audio.voices import cast
    from app.domain.models import CasePlan
    from app.models import Character

    voice = await best_free_voice()
    async with session_factory()() as s:
        ids = [c.id for c in (await s.execute(select(Case).where(Case.status == Phase.COURTROOM_READY.value))).scalars()]
    for case_id in ids:
        async with session_factory()() as s:
            case = await cs.load_case(s, case_id)
            cv = await cs.current_version(s, case) if case else None
            if not case or not cv:
                continue
            plan = CasePlan.model_validate(cv.plan)
            choices = cast(plan.characters)
            specs = {c.key: c for c in plan.characters}
            for ch in case.characters:
                ch_row: Character = ch
                v, spec = choices.get(ch_row.key), specs.get(ch_row.key)
                if not v or not ch_row.voice or not spec:
                    continue
                ch_row.voice.voice_id = v.fish_voice_id
                ch_row.voice.voice_label = v.label
                ch_row.voice.base_direction = v.base_direction
                ch_row.voice.mock_params = {**(ch_row.voice.mock_params or {}), "pace": spec.voice.pace}
            cs.advance(case, Phase.AUDIO_PREPARATION)
            case.audio_provider = voice
            await s.commit()
            case = await cs.load_case(s, case_id)
            out = await _synthesize(s, case, _noop, voice)
            log.info("re-cast %s: %s", case.slug, {k: out[k] for k in ("synthesized", "cached", "blocked", "failed")})


async def main(showcase_only: bool, recast: bool = False) -> None:
    if recast:
        await seed_showcase()
        await recast_all()
        return
    await seed_showcase()
    if not showcase_only:
        await seed_curated()
    await revoice()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--showcase", action="store_true")
    p.add_argument("--recast", action="store_true", help="re-cast voices for every case and re-record")
    a = p.parse_args()
    asyncio.run(main(a.showcase, a.recast))
