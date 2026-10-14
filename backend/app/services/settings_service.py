"""Runtime settings + provider eligibility. The environment stays authoritative
for anything that can spend money."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import AppSetting


async def get_value(s: AsyncSession, key: str, default=None):
    row = await s.get(AppSetting, key)
    return row.value.get("v", default) if row else default


async def set_value(s: AsyncSession, key: str, value) -> None:
    row = await s.get(AppSetting, key)
    if row:
        row.value = {"v": value}
    else:
        s.add(AppSetting(key=key, value={"v": value}))


async def provider_status(s: AsyncSession) -> dict:
    cfg = get_settings()
    free_verified = bool(await get_value(s, "fish_free_verified", False))
    has_key = bool(cfg.fish_audio_api_key)
    return {
        "audio": {
            "mock": {"available": True, "billable": False, "reason": "Local procedural voices"},
            "fish-free": {
                "available": has_key and free_verified, "billable": False, "model": "s2.1-pro-free",
                "reason": "ready" if has_key and free_verified else
                ("Run the free-tier verification first" if has_key else "FISH_AUDIO_API_KEY not set"),
            },
            "drama3": {
                "available": cfg.paid_tts_armed, "billable": True, "model": "drama-3",
                "reason": "armed — every case still needs explicit authorisation" if cfg.paid_tts_armed else
                "disabled (set AUDIO_PROVIDER=drama3, ENABLE_PAID_TTS=true, FISH_AUDIO_API_KEY)",
            },
        },
        "llm": {
            "mock": {"available": True},
            "ollama": {"available": True, "model": cfg.ollama_model},
            "anthropic": {"available": bool(cfg.anthropic_api_key), "model": cfg.anthropic_model},
        },
    }


async def effective_providers(s: AsyncSession, llm: str | None, audio: str | None) -> tuple[str, str]:
    cfg = get_settings()
    status = await provider_status(s)
    llm = llm or await get_value(s, "default_llm_provider", None) or cfg.llm_provider
    audio = audio or await get_value(s, "default_audio_provider", None) or cfg.audio_provider
    if not status["llm"].get(llm, {}).get("available"):
        llm = "mock"
    if not status["audio"].get(audio, {}).get("available"):
        audio = "mock"  # never silently upgrade to a paid provider; fall back to free
    return llm, audio
