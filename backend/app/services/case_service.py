"""CaseService: create cases, persist generated plans/scripts, load them back."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.director import CaseInput
from app.audio.voices import cast
from app.domain.models import CasePlan, Phase, TrialScript
from app.domain.state_machine import TransitionContext, transition
from app.models import (
    Case,
    CaseVersion,
    Character,
    DialogueTurnRow,
    EvidenceItem,
    SceneRow,
    VoiceAssignment,
    WitnessStatement,
)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]
    return f"{s or 'case'}-{secrets.token_hex(3)}"


async def next_case_number(session: AsyncSession) -> str:
    n = (await session.execute(select(func.count(Case.id)))).scalar_one()
    return f"CR-{datetime.now(UTC).year}-{n + 101:04d}"


async def create_case(session: AsyncSession, data: dict, llm_provider: str, audio_provider: str) -> Case:
    case = Case(
        slug=slugify(data["defendant"]),
        defendant=data["defendant"].strip(),
        accusation=data["accusation"].strip(),
        context=(data.get("context") or "").strip(),
        language=data.get("language", "en"),
        comedy_intensity=data.get("comedy_intensity", "unserious"),
        drama_level=int(data.get("drama_level", 60)),
        trial_length=data.get("trial_length", "quick"),
        participation_mode=data.get("participation_mode", "jury"),
        case_number=await next_case_number(session),
        llm_provider=llm_provider,
        audio_provider=audio_provider,
        status=Phase.CASE_CREATED.value,
    )
    session.add(case)
    await session.flush()
    return case


def case_input(case: Case) -> CaseInput:
    return CaseInput(
        case_id=case.id, defendant=case.defendant, accusation=case.accusation, context=case.context,
        language=case.language, comedy_intensity=case.comedy_intensity, drama_level=case.drama_level,
        trial_length=case.trial_length, participation_mode=case.participation_mode, case_number=case.case_number,
    )


def advance(case: Case, target: Phase, **ctx) -> None:
    case.status = transition(case.status, target, TransitionContext(**ctx)).value


async def save_trial(session: AsyncSession, case: Case, plan: CasePlan, script: TrialScript, *,
                     humor: list[dict], validation: dict, generator: str) -> CaseVersion:
    """Persist a generated trial as a new immutable version and the live relational rows."""
    version = case.current_version + 1
    cv = CaseVersion(case_id=case.id, version=version, plan=plan.model_dump(mode="json"),
                     script=script.model_dump(mode="json"), humor_report={"scenes": humor},
                     validation_report=validation, generator=generator)
    session.add(cv)

    # Replace the live projection of the case (older versions stay in case_versions).
    scene_ids = select(SceneRow.id).where(SceneRow.case_id == case.id)
    await session.execute(delete(DialogueTurnRow).where(DialogueTurnRow.scene_id.in_(scene_ids)))
    for model in (SceneRow, EvidenceItem, WitnessStatement, Character):
        await session.execute(delete(model).where(model.case_id == case.id))
    await session.flush()

    voices = cast(plan.characters)
    for c in plan.characters:
        ch = Character(case_id=case.id, key=c.key, role=c.role, name=c.name, spec=c.model_dump(mode="json"))
        session.add(ch)
        await session.flush()
        v = voices[c.key]
        session.add(VoiceAssignment(character_id=ch.id, provider=case.audio_provider, voice_id=v.fish_voice_id,
                                    voice_label=v.label, base_direction=v.base_direction,
                                    mock_params={"f0": v.mock.f0, "speed": v.mock.speed, "brightness": v.mock.brightness,
                                                 "breath": v.mock.breath, "wobble": v.mock.wobble, "shape": v.mock.shape,
                                                 "pace": c.voice.pace}))
    for e in plan.evidence:
        session.add(EvidenceItem(case_id=case.id, exhibit=e.id, title=e.title, spec=e.model_dump(mode="json")))

    report_by_scene = {h["scene_id"]: h for h in humor}
    for order, scene in enumerate(script.scenes):
        row = SceneRow(case_id=case.id, scene_key=scene.id, order=order, phase=scene.phase.value, title=scene.title,
                       strategy=scene.strategy, branch=scene.branch,
                       window=scene.window.model_dump(mode="json") if scene.window else None,
                       humor_score=report_by_scene.get(scene.id, {}).get("overall"))
        session.add(row)
        await session.flush()
        for i, t in enumerate(scene.turns):
            session.add(_turn_row(row.id, t, i, None))
            if t.kind == "testimony":
                session.add(WitnessStatement(case_id=case.id, witness_key=t.speaker, turn_key=t.id, statement=t.subtitle))
        if scene.window:
            for opt in scene.window.options:
                for i, t in enumerate(opt.response):
                    session.add(_turn_row(row.id, t, i, opt.id))

    case.current_version = version
    case.title = plan.title
    return cv


def _turn_row(scene_id: str, t, order: int, branch: str | None, session_id: str | None = None) -> DialogueTurnRow:
    return DialogueTurnRow(scene_id=scene_id, turn_key=t.id, branch_key=branch, order=order, speaker=t.speaker,
                           text=t.text, data=t.model_dump(mode="json"), session_id=session_id)


async def load_case(session: AsyncSession, case_ref: str) -> Case | None:
    q = select(Case).where((Case.id == case_ref) | (Case.slug == case_ref)).options(
        selectinload(Case.characters).selectinload(Character.voice),
        selectinload(Case.evidence),
        selectinload(Case.scenes).selectinload(SceneRow.turns).selectinload(DialogueTurnRow.audio),
    ).execution_options(populate_existing=True)
    return (await session.execute(q)).scalar_one_or_none()


async def current_version(session: AsyncSession, case: Case) -> CaseVersion | None:
    q = select(CaseVersion).where(CaseVersion.case_id == case.id, CaseVersion.version == case.current_version)
    return (await session.execute(q)).scalar_one_or_none()


async def load_plan_script(session: AsyncSession, case: Case) -> tuple[CasePlan, TrialScript] | None:
    cv = await current_version(session, case)
    if not cv or not cv.script:
        return None
    return CasePlan.model_validate(cv.plan), TrialScript.model_validate(cv.script)
