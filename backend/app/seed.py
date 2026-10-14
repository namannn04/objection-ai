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
from app.services.pipeline import _synthesize, prepare_case
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
                        is_featured=True, llm_provider="hand-authored", audio_provider="mock", status=Phase.CASE_CREATED.value)
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
        out = await _synthesize(s, case, _noop, "mock")
        log.info("showcase audio: %s", {k: out[k] for k in ("total", "synthesized", "cached")})
        return case.id


async def seed_curated() -> None:
    from app.models import AudioGenerationJob

    for spec in CURATED:
        async with session_factory()() as s:
            exists = (await s.execute(select(Case).where(Case.defendant == spec["defendant"], Case.is_featured.is_(True)))).scalar_one_or_none()
            if exists:
                continue
            case = await cs.create_case(s, {**spec, "participation_mode": "jury", "drama_level": 65}, "mock", "mock")
            case.is_featured = True
            job = AudioGenerationJob(kind="prepare_case", case_id=case.id, status="running")
            s.add(job)
            await s.commit()
            await prepare_case(s, job, _noop)
            job.status = "done"
            await s.commit()
            log.info("curated case ready: %s", case.slug)


async def main(showcase_only: bool) -> None:
    await seed_showcase()
    if not showcase_only:
        await seed_curated()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--showcase", action="store_true")
    asyncio.run(main(p.parse_args().showcase))
