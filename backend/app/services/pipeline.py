"""Job handlers: case preparation (agents → script) and audio preparation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import generate_trial
from app.audio.providers import get_audio_provider
from app.config import get_settings
from app.db import session_factory
from app.domain.models import Phase
from app.llm.providers import get_llm
from app.models import AudioGenerationJob, Case, DialogueTurnRow, SceneRow
from app.services import case_service as cs
from app.services.audio_generation import AudioGenerationService, ensure_sfx_fixtures
from app.services.jobs import FAIL_HOOKS, enqueue, handler


def roles_of(case: Case) -> frozenset[str]:
    return frozenset(c.role for c in case.characters)


@handler("prepare_case")
async def prepare_case(s: AsyncSession, job: AudioGenerationJob, progress) -> dict:
    case = await cs.load_case(s, job.case_id)  # type: ignore[arg-type]
    assert case
    if case.status in (Phase.CASE_CREATED.value, Phase.FAILED.value):
        cs.advance(case, Phase.CASE_PREPARATION)
    cs.advance(case, Phase.SCRIPT_PLANNING)
    case.status_detail = "The judge is questioning their career choices."
    await s.commit()
    await progress("status", {"status": case.status})

    llm = get_llm(case.llm_provider)
    state = await generate_trial(llm, cs.case_input(case), progress)
    sources = dict(state["sources"])
    cs.advance(case, Phase.SCRIPT_VALIDATION)
    report = state["validation"]
    await cs.save_trial(s, case, state["plan"], state["script"], humor=state["reports"],
                        validation=report.model_dump(), generator=f"{llm.name}:{sources}")
    await s.commit()
    await progress("status", {"status": case.status, "validation": report.model_dump()})
    if not report.valid:
        cs.advance(case, Phase.FAILED)
        case.status_detail = "Script failed validation: " + "; ".join(report.errors[:3])
        await s.commit()
        return {"_status": "failed", "errors": report.errors}

    cs.advance(case, Phase.AUDIO_PREPARATION, script_valid=True)
    await s.commit()
    case = await cs.load_case(s, case.id)
    assert case
    provider = get_audio_provider(get_settings(), case.audio_provider)
    if provider.billable:
        case.status_detail = "awaiting_authorization"
        await s.commit()
        await progress("status", {"status": case.status, "detail": case.status_detail})
        return {"sources": sources, "awaiting_authorization": True}
    return {"sources": sources, **(await _synthesize(s, case, progress, provider.name))}


async def all_rows(s: AsyncSession, case: Case) -> list[DialogueTurnRow]:
    q = (select(DialogueTurnRow).join(SceneRow).where(SceneRow.case_id == case.id, DialogueTurnRow.session_id.is_(None))
         .order_by(SceneRow.order, DialogueTurnRow.branch_key.nullsfirst(), DialogueTurnRow.order))
    return list((await s.execute(q)).scalars())


async def _synthesize(s: AsyncSession, case: Case, progress, provider_name: str, allow_reserve: bool = False) -> dict:
    ensure_sfx_fixtures()
    svc = AudioGenerationService(get_audio_provider(get_settings(), provider_name))
    case.status_detail = f"Recording the hearing ({provider_name} voices)…"
    await s.commit()
    rows = await all_rows(s, case)
    rep = await svc.prepare(s, case, rows, progress, allow_reserve=allow_reserve)
    summary = {"total": rep.total, "cached": rep.cached, "synthesized": rep.synthesized, "blocked": rep.blocked,
               "failed": rep.failed, "characters": rep.characters, "estimated_cost_usd": rep.estimated_cost_usd,
               "errors": rep.errors[:5], "provider": provider_name}
    if rep.complete:
        cs.advance(case, Phase.COURTROOM_READY, audio_ready=True)
        case.status_detail = ""
        case.audio_provider = provider_name
    else:
        case.status_detail = ("blocked: " if rep.blocked else "failed: ") + (rep.errors[0] if rep.errors else "")
    await s.commit()
    await progress("status", {"status": case.status, "detail": case.status_detail, "audio": summary})
    return {**summary, "_status": "done" if rep.complete else ("blocked" if rep.blocked else "failed")}


@handler("synthesize_case")
async def synthesize_case(s: AsyncSession, job: AudioGenerationJob, progress) -> dict:
    case = await cs.load_case(s, job.case_id)  # type: ignore[arg-type]
    assert case
    if case.status == Phase.COURTROOM_READY.value:
        cs.advance(case, Phase.AUDIO_PREPARATION)
    if case.status != Phase.AUDIO_PREPARATION.value:
        raise ValueError(f"case is {case.status}; cannot prepare audio")
    return await _synthesize(s, case, progress, job.payload.get("provider") or case.audio_provider,
                             allow_reserve=bool(job.payload.get("allow_reserve")))


async def _mark_failed(job_id: str, error: str) -> None:
    async with session_factory()() as s:
        job = await s.get(AudioGenerationJob, job_id)
        case = await s.get(Case, job.case_id) if job and job.case_id else None
        if case and case.status in (Phase.CASE_PREPARATION.value, Phase.SCRIPT_PLANNING.value,
                                    Phase.SCRIPT_VALIDATION.value, Phase.CASE_CREATED.value):
            cs.advance(case, Phase.FAILED)
            case.status_detail = f"Preparation failed: {error[:200]}"
            await s.commit()
        elif case and case.status == Phase.AUDIO_PREPARATION.value:
            case.status_detail = f"failed: {error[:200]}"  # stays retryable
            await s.commit()


FAIL_HOOKS["prepare_case"] = _mark_failed
FAIL_HOOKS["synthesize_case"] = _mark_failed


async def start_preparation(s: AsyncSession, case: Case) -> str:
    job = await enqueue(s, "prepare_case", case.id)
    return job.id
