"""Script validation: structural, referential and safety checks before any audio is made."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.domain.models import TRIAL_PHASES, CasePlan, Phase, TrialScript
from app.domain.state_machine import TRANSITIONS

_BLOCKLIST = re.compile(
    r"\b(kill yourself|kys|suicide|rape|nazi|terroris[mt]|genocide|slur)\b", re.IGNORECASE
)


class ValidationReport(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


def validate_script(plan: CasePlan, script: TrialScript) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    keys = {c.key for c in plan.characters}
    roles = {c.role for c in plan.characters}
    for need in ("judge", "prosecutor", "defense", "defendant"):
        if need not in roles:
            errors.append(f"missing required role: {need}")
    exhibits = {e.id for e in plan.evidence}

    seen_ids: set[str] = set()
    for t in script.all_turns():
        if t.id in seen_ids:
            errors.append(f"duplicate turn id {t.id}")
        seen_ids.add(t.id)
        if t.speaker not in keys:
            errors.append(f"turn {t.id}: unknown speaker {t.speaker}")
        if not t.subtitle:
            errors.append(f"turn {t.id}: empty dialogue")
        if t.evidence_id and t.evidence_id not in exhibits:
            errors.append(f"turn {t.id}: unknown exhibit {t.evidence_id}")
        if _BLOCKLIST.search(t.text):
            errors.append(f"turn {t.id}: failed content safety check")
        for k in t.reactions:
            if k not in keys:
                warnings.append(f"turn {t.id}: reaction from unknown character {k}")

    main = script.main_scenes()
    if not main:
        errors.append("script has no scenes")
    # Phase order must be a legal path through the state machine.
    prev = Phase.COURTROOM_READY
    for s in main:
        if s.phase != prev and s.phase not in TRANSITIONS[prev]:
            errors.append(f"scene {s.id}: illegal phase order {prev} → {s.phase}")
        prev = s.phase
        if s.phase not in TRIAL_PHASES:
            errors.append(f"scene {s.id}: {s.phase} is not a trial phase")
        if s.window:
            ids = [o.id for o in s.window.options]
            if len(ids) != len(set(ids)):
                errors.append(f"scene {s.id}: duplicate option ids")
    if prev != Phase.DELIBERATION:
        errors.append("main trial must end in DELIBERATION")
    for guilty in (True, False):
        if script.verdict_scene(guilty) is None:
            errors.append(f"missing {'guilty' if guilty else 'not-guilty'} verdict branch")

    scene_ids = [s.id for s in script.scenes]
    if len(scene_ids) != len(set(scene_ids)):
        errors.append("duplicate scene ids")

    turns = script.all_turns()
    chars = sum(len(t.text) for t in turns)
    stats = {
        "scenes": len(script.scenes),
        "turns": len(turns),
        "main_turns": sum(len(s.turns) for s in main),
        "characters": chars,
        "speakers": sorted({t.speaker for t in turns}),
    }
    if chars > 12000:
        warnings.append(f"script is long ({chars} characters); consider a shorter trial for paid audio")
    return ValidationReport(valid=not errors, errors=errors, warnings=warnings, stats=stats)
