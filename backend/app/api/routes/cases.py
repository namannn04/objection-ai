from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_case_or_404
from app.audio.providers import get_audio_provider
from app.config import get_settings
from app.db import get_session
from app.domain.models import Phase
from app.domain.validation import validate_script
from app.models import AudioGenerationJob, Case
from app.schemas.api import AudioAuthorizeIn, AudioPrepareIn, CaseCreate, CaseCreated, CaseSummary, JobOut
from app.services import case_service as cs
from app.services.audio_generation import AudioGenerationService
from app.services.events import bus
from app.services.jobs import enqueue
from app.services.manifest import build_manifest
from app.services.pipeline import all_rows
from app.services.settings_service import effective_providers, provider_status

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseCreated, status_code=201, summary="File a case (starts preparation)")
async def create_case(body: CaseCreate, s: AsyncSession = Depends(get_session)):
    llm, audio = await effective_providers(s, body.llm_provider, body.audio_provider)
    case = await cs.create_case(s, body.model_dump(), llm, audio)
    job = await enqueue(s, "prepare_case", case.id)
    await s.commit()
    return CaseCreated(case=CaseSummary.model_validate(case), job_id=job.id)


@router.get("", response_model=list[CaseSummary], summary="List cases")
async def list_cases(showcase: bool | None = None, limit: int = Query(30, le=100), s: AsyncSession = Depends(get_session)):
    q = select(Case).order_by(Case.is_featured.desc(), Case.created_at.desc()).limit(limit)
    if showcase is not None:
        q = q.where(Case.is_showcase.is_(showcase))
    return [CaseSummary.model_validate(c) for c in (await s.execute(q)).scalars()]


@router.get("/{ref}", summary="Case detail with plan, cast, evidence and reports")
async def get_case(ref: str, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    cv = await cs.current_version(s, case)
    plan = cv.plan if cv else None
    return {
        "case": CaseSummary.model_validate(case).model_dump(mode="json"),
        "plan": plan and {k: plan[k] for k in ("title", "case_number", "accusation_summary", "charges",
                                               "defendant_profile", "prosecutor_strategy", "defense_strategy",
                                               "outline", "comedic_moments", "running_gags", "punishments")},
        "characters": plan and [
            {k: c.get(k) for k in ("key", "role", "name", "title", "personality", "speaking_style",
                                    "relationship_to_case", "visual", "surprise")} for c in plan["characters"]],
        "evidence": plan and plan["evidence"],
        "humor_report": cv.humor_report if cv else None,
        "validation": cv.validation_report if cv else None,
        "generator": cv.generator if cv else None,
        "versions": case.current_version,
    }


@router.get("/{ref}/status", summary="Processing status and latest job")
async def case_status(ref: str, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    job = (await s.execute(select(AudioGenerationJob).where(AudioGenerationJob.case_id == case.id)
                           .order_by(AudioGenerationJob.created_at.desc()).limit(1))).scalar_one_or_none()
    return {"status": case.status, "detail": case.status_detail, "title": case.title,
            "job": JobOut.model_validate(job).model_dump(mode="json") if job else None}


@router.get("/{ref}/events", summary="Live preparation events (SSE)")
async def case_events(ref: str, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    channel = f"case:{case.id}"

    async def stream():
        yield {"event": "hello", "data": "{}"}
        import json

        async for msg in bus.subscribe(channel):
            yield {"event": msg["event"], "data": json.dumps(msg["data"], default=str)}

    return EventSourceResponse(stream(), ping=15)


@router.post("/{ref}/prepare", response_model=JobOut, summary="(Re)generate the case plan and trial script")
async def regenerate(ref: str, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    if case.is_showcase:
        raise HTTPException(409, "The showcase case is hand-authored and cached; it is never regenerated.")
    busy = case.status in (Phase.CASE_PREPARATION.value, Phase.SCRIPT_PLANNING.value, Phase.SCRIPT_VALIDATION.value)
    if busy:
        raise HTTPException(409, "case is already being prepared")
    if case.status not in (Phase.FAILED.value, Phase.CASE_CREATED.value):
        case.status = Phase.FAILED.value  # explicit restart path: FAILED → CASE_PREPARATION
    job = await enqueue(s, "prepare_case", case.id)
    await s.commit()
    return JobOut.model_validate(job)


@router.post("/{ref}/validate", summary="Re-run script validation on the current version")
async def validate(ref: str, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    ps = await cs.load_plan_script(s, case)
    if not ps:
        raise HTTPException(409, "case has no script yet")
    return validate_script(*ps).model_dump()


@router.get("/{ref}/manifest", summary="Playback manifest")
async def manifest(ref: str, session_id: str | None = None, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    if not case.scenes:
        raise HTTPException(409, "case has no script yet")
    return build_manifest(case, session_id=session_id)


@router.get("/{ref}/audio/estimate", summary="Projected audio generation cost")
async def audio_estimate(ref: str, provider: str | None = None, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    provider = provider or case.audio_provider
    if provider not in ("mock", "fish-free", "drama3"):
        raise HTTPException(422, "unknown provider")
    cfg = get_settings()
    svc = AudioGenerationService(get_audio_provider(cfg, provider))
    rep = await svc.estimate(s, case, await all_rows(s, case))
    from app.audio.budget import spent, verified_balance

    case_chars, _ = await spent(s, case.id)
    total_chars, total_cost = await spent(s)
    status = await provider_status(s)
    return {
        "provider": provider, "model": svc.provider.model, "billable": svc.provider.billable,
        "lines": rep.total, "cached_lines": rep.cached, "characters_to_generate": rep.characters,
        "estimated_cost_usd": rep.estimated_cost_usd,
        "price_basis": f"${cfg.drama3_usd_per_million_chars:g} per 1M characters (Drama 3 list price; conservative)"
        if provider == "drama3" else "free",
        "limits": {"max_characters_per_case": cfg.drama3_max_characters_per_case,
                   "case_characters_spent": case_chars,
                   "max_projected_spend_usd": cfg.drama3_max_projected_spend_usd,
                   "projected_spend_so_far_usd": round(total_cost, 4), "total_billable_characters": total_chars,
                   "demo_reserve_usd": cfg.drama3_demo_reserve_usd},
        "verified_balance_usd": await verified_balance(s),
        "provider_available": status["audio"][provider]["available"],
        "provider_reason": status["audio"][provider]["reason"],
        "authorized": case.paid_audio_authorized,
        "note": "Estimates are application-side; Fish Audio exposes no per-request usage endpoint.",
    }


@router.post("/{ref}/audio/prepare", response_model=JobOut, summary="Prepare audio with a free provider")
async def audio_prepare(ref: str, body: AudioPrepareIn, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    status = await provider_status(s)
    if not status["audio"][body.provider]["available"]:
        raise HTTPException(409, status["audio"][body.provider]["reason"])
    if case.status not in (Phase.AUDIO_PREPARATION.value, Phase.COURTROOM_READY.value):
        raise HTTPException(409, f"case is {case.status}")
    job = await enqueue(s, "synthesize_case", case.id, {"provider": body.provider})
    await s.commit()
    return JobOut.model_validate(job)


@router.post("/{ref}/audio/authorize", response_model=JobOut, summary="Explicitly authorise paid Drama 3 synthesis")
async def audio_authorize(ref: str, body: AudioAuthorizeIn, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    cfg = get_settings()
    if not cfg.paid_tts_armed:
        raise HTTPException(409, "Paid synthesis is disabled in the server environment.")
    if case.status not in (Phase.AUDIO_PREPARATION.value, Phase.COURTROOM_READY.value):
        raise HTTPException(409, f"case is {case.status}")
    svc = AudioGenerationService(get_audio_provider(cfg, "drama3"))
    rep = await svc.estimate(s, case, await all_rows(s, case))
    if abs(rep.estimated_cost_usd - body.expected_cost_usd) > 0.0005:
        raise HTTPException(409, f"Estimate changed to ${rep.estimated_cost_usd:.4f}; review it again before confirming.")
    case.paid_audio_authorized = True
    job = await enqueue(s, "synthesize_case", case.id, {"provider": "drama3", "allow_reserve": body.allow_reserve})
    await s.commit()
    return JobOut.model_validate(job)
