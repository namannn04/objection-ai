from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio.budget import spent, verified_balance
from app.config import get_settings
from app.db import get_session
from app.models import AppSetting, UsageRecord
from app.schemas.api import SettingsPatch
from app.services.settings_service import get_value, provider_status, set_value

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health(s: AsyncSession = Depends(get_session)):
    await s.execute(select(1))
    return {"ok": True}


@router.get("/settings", summary="Provider configuration and defaults")
async def settings(s: AsyncSession = Depends(get_session)):
    cfg = get_settings()
    return {
        "providers": await provider_status(s),
        "defaults": {
            "llm": await get_value(s, "default_llm_provider", cfg.llm_provider),
            "audio": await get_value(s, "default_audio_provider", cfg.audio_provider),
        },
        "paid_tts_armed": cfg.paid_tts_armed,
    }


@router.patch("/settings", summary="Update runtime defaults")
async def patch_settings(body: SettingsPatch, s: AsyncSession = Depends(get_session)):
    status = await provider_status(s)
    if body.default_audio_provider:
        if not status["audio"][body.default_audio_provider]["available"]:
            raise HTTPException(409, status["audio"][body.default_audio_provider]["reason"])
        await set_value(s, "default_audio_provider", body.default_audio_provider)
    if body.default_llm_provider:
        if not status["llm"][body.default_llm_provider]["available"]:
            raise HTTPException(409, f"{body.default_llm_provider} is not configured")
        await set_value(s, "default_llm_provider", body.default_llm_provider)
    await s.commit()
    return await settings(s)


@router.get("/usage", summary="Usage estimates and audit log")
async def usage(limit: int = 50, s: AsyncSession = Depends(get_session)):
    cfg = get_settings()
    chars, cost = await spent(s)
    rows = (await s.execute(select(UsageRecord).order_by(UsageRecord.created_at.desc()).limit(min(limit, 200)))).scalars()
    outcomes = dict((await s.execute(select(UsageRecord.outcome, func.count()).group_by(UsageRecord.outcome))).all())
    bal = await s.get(AppSetting, "fish_balance")
    return {
        "billable_characters": chars,
        "estimated_spend_usd": round(cost, 4),
        "ceiling_usd": cfg.drama3_max_projected_spend_usd,
        "remaining_under_ceiling_usd": round(max(0.0, cfg.drama3_max_projected_spend_usd - cost), 4),
        "demo_reserve_usd": cfg.drama3_demo_reserve_usd,
        "verified_balance_usd": await verified_balance(s),
        "verified_balance_checked_at": bal.updated_at if bal else None,
        "outcomes": outcomes,
        "records": [
            {"at": r.created_at, "case_id": r.case_id, "provider": r.provider, "model": r.model,
             "characters": r.characters, "estimated_cost_usd": r.estimated_cost_usd, "outcome": r.outcome,
             "detail": r.detail, "billable": r.billable}
            for r in rows
        ],
        "note": "Spend is an application-side estimate. Only the balance refreshed from Fish Audio is verified.",
    }


@router.post("/usage/balance/refresh", summary="Fetch the verified Fish Audio balance (free GET)")
async def refresh_balance(s: AsyncSession = Depends(get_session)):
    from app.audio.providers import FishAudioProvider

    cfg = get_settings()
    if not cfg.fish_audio_api_key:
        raise HTTPException(409, "FISH_AUDIO_API_KEY not set")
    try:
        data = await FishAudioProvider(cfg, "fish-free").balance()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"balance lookup failed: {exc}") from exc
    row = await s.get(AppSetting, "fish_balance")
    value = {"credit": data.get("credit"), "raw": {k: data.get(k) for k in ("credit", "cumulative_top_up", "updated_at")}}
    if row:
        row.value = value
    else:
        s.add(AppSetting(key="fish_balance", value=value))
    await s.commit()
    return value
