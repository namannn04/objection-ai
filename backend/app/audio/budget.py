"""BudgetGuard: application-level protection for paid Drama 3 credit.

These are *application* controls, not provider-enforced limits. A request is
allowed only if every one of these holds:
  1. paid TTS is armed (AUDIO_PROVIDER=drama3, ENABLE_PAID_TTS=true, key set)
  2. this case was explicitly authorised after its estimate was shown
  3. the case stays under DRAMA3_MAX_CHARACTERS_PER_CASE
  4. projected total spend stays under DRAMA3_MAX_PROJECTED_SPEND_USD
  5. a verified balance (if known) stays above the demo reserve
  6. the identical request is not in flight, and never ended "uncertain"
Every decision is written to the usage audit log.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio.compiler import CompiledRequest
from app.config import Settings
from app.models import AppSetting, Case, UsageRecord

SPENDING = ("synthesized", "uncertain")
_inflight: set[str] = set()
_lock = asyncio.Lock()


class BudgetBlocked(Exception):
    def __init__(self, reason: str, code: str):
        super().__init__(reason)
        self.code = code


@dataclass(slots=True)
class Decision:
    allowed: bool
    cost_usd: float
    reason: str = ""
    code: str = ""


def estimate_cost(settings: Settings, provider: str, characters: int) -> float:
    if provider != "drama3":
        return 0.0
    return round(characters * settings.drama3_usd_per_million_chars / 1_000_000, 6)


async def spent(session: AsyncSession, case_id: str | None = None) -> tuple[int, float]:
    q = select(func.coalesce(func.sum(UsageRecord.characters), 0), func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0.0)).where(
        UsageRecord.billable.is_(True), UsageRecord.outcome.in_(SPENDING)
    )
    if case_id:
        q = q.where(UsageRecord.case_id == case_id)
    chars, cost = (await session.execute(q)).one()
    return int(chars), float(cost)


async def verified_balance(session: AsyncSession) -> float | None:
    row = await session.get(AppSetting, "fish_balance")
    try:
        return float(row.value["credit"]) if row else None
    except (KeyError, TypeError, ValueError):
        return None


class BudgetGuard:
    def __init__(self, settings: Settings):
        self.s = settings

    async def check(self, session: AsyncSession, case: Case | None, req: CompiledRequest, *, billable: bool,
                    allow_reserve: bool = False, extra_chars: int = 0, extra_cost: float = 0.0) -> Decision:
        """`extra_*` = requests already approved earlier in the same batch."""
        cost = estimate_cost(self.s, req.provider, req.characters) if billable else 0.0
        if not billable:
            return Decision(True, 0.0)
        s = self.s
        if not s.paid_tts_armed:
            return Decision(False, cost, "Paid Drama 3 synthesis is disabled (needs AUDIO_PROVIDER=drama3, "
                            "ENABLE_PAID_TTS=true and FISH_AUDIO_API_KEY).", "paid_disabled")
        if case is None or not case.paid_audio_authorized:
            return Decision(False, cost, "This case has not been authorised for paid audio. Review the estimate "
                            "and confirm first.", "not_authorized")
        case_chars, _ = await spent(session, case.id)
        if case_chars + extra_chars + req.characters > s.drama3_max_characters_per_case:
            return Decision(False, cost, f"Case character limit reached ({case_chars + extra_chars + req.characters} > "
                            f"{s.drama3_max_characters_per_case}).", "case_limit")
        _, total = await spent(session)
        if total + extra_cost + cost > s.drama3_max_projected_spend_usd:
            return Decision(False, cost, f"Projected spend ${total + extra_cost + cost:.4f} would exceed the "
                            f"${s.drama3_max_projected_spend_usd:.2f} ceiling.", "spend_ceiling")
        bal = await verified_balance(session)
        if bal is not None and not allow_reserve and bal - extra_cost - cost < s.drama3_demo_reserve_usd:
            return Decision(False, cost, f"Would dip into the ${s.drama3_demo_reserve_usd:.2f} demo reserve "
                            f"(verified balance ${bal:.2f}).", "reserve")
        dup = (await session.execute(
            select(UsageRecord.outcome).where(UsageRecord.request_hash == req.cache_key, UsageRecord.billable.is_(True),
                                              UsageRecord.outcome == "uncertain").limit(1)
        )).scalar_one_or_none()
        if dup:
            return Decision(False, cost, "An identical request previously ended in an uncertain state (possibly "
                            "billed). Not retrying automatically.", "uncertain_duplicate")
        return Decision(True, cost)

    async def acquire(self, key: str) -> bool:
        async with _lock:
            if key in _inflight:
                return False
            _inflight.add(key)
            return True

    async def release(self, key: str) -> None:
        async with _lock:
            _inflight.discard(key)


async def record(session: AsyncSession, *, case_id: str | None, req: CompiledRequest, outcome: str, cost: float,
                 billable: bool, detail: str = "") -> None:
    session.add(UsageRecord(case_id=case_id, provider=req.provider, model=req.model, request_hash=req.cache_key,
                            characters=req.characters, estimated_cost_usd=cost if outcome in SPENDING else 0.0,
                            outcome=outcome, detail=detail[:500], billable=billable))
