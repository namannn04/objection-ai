"""InterventionService: chaos-mode free-text interventions, generated live.

1. validate (window open, chaos mode, one per window, content safety)
2. record the intervention, queue a job (the trial waits at a safe point)
3. the job: the judge rules and one character responds, via their own agents
   (scripted fallback on LLM failure), persisted as a session-only branch
4. voice it with the case's provider; fall back to mock voices if paid audio
   is not permitted, and mark that clearly
"""

from __future__ import annotations

import random
import re

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agents import TurnContext, TurnDraft, agent_for, to_turn
from app.agents.blueprint import SceneSpec, Slot
from app.agents.director import SceneBrief
from app.agents.topic import seed_for
from app.audio.providers import get_audio_provider
from app.config import get_settings
from app.domain.models import CasePlan, DialogueTurn, Phase
from app.domain.validation import _BLOCKLIST
from app.llm.providers import get_llm
from app.models import AudioGenerationJob, CourtroomSession, DialogueTurnRow, SceneRow, UserIntervention
from app.services import case_service as cs
from app.services.audio_generation import AudioGenerationService
from app.services.jobs import enqueue, handler
from app.services.session_service import SessionError, load_session


async def submit_free_text(s: AsyncSession, sess: CourtroomSession, case, scene_key: str, text: str) -> dict:
    if sess.participation_mode != "chaos":
        raise SessionError("Free-text interventions are only allowed in chaos mode.", 403)
    if sess.open_window_scene != scene_key:
        raise SessionError("that window is not open")
    if any(i.scene_key == scene_key and i.status != "rejected" for i in sess.interventions):
        raise SessionError("the jury already spoke in this window", 429)
    if _BLOCKLIST.search(text):
        raise SessionError("The court will not entertain that. Keep it fictional and kind.", 422)
    iv = UserIntervention(session_id=sess.id, scene_key=scene_key, kind="free", free_text=text,
                          status="generating", source="live")
    s.add(iv)
    sess.interventions.append(iv)
    await s.flush()
    job = await enqueue(s, "intervention", case.id, {"intervention_id": iv.id, "session_id": sess.id})
    return {"intervention_id": iv.id, "job_id": job.id, "status": "generating"}


class Ruling(BaseModel):
    kind: str = Field(description="objection | question | demand | other")
    ruling: str = Field(description="sustained | overruled | allowed | denied")
    responder: str = Field(description="character key who answers after the judge")
    favours: str = Field(description="prosecution | defense | none — who the intervention helps")


def _classify_fallback(text: str, plan: CasePlan) -> Ruling:
    t = text.lower()
    kind = "objection" if "objection" in t else "question" if t.rstrip().endswith("?") else "demand" if re.search(r"\b(demand|call|show|see|bring)\b", t) else "other"
    responder = next((c.key for c in plan.characters if c.role in ("witness", "defendant") and c.name.lower().replace("the ", "") in t), "defendant")
    r = random.Random(seed_for(text))
    ruling = {"objection": r.choice(["sustained", "overruled"]), "question": "allowed", "demand": r.choice(["allowed", "denied"])}.get(kind, "allowed")
    favours = "defense" if ruling == "sustained" else "prosecution" if kind == "demand" else "none"
    return Ruling(kind=kind, ruling=ruling, responder=responder, favours=favours)


_JUDGE_FALLBACK = {
    "sustained": "Sustained. [pause] I can't believe I'm saying this, but the jury has a point.",
    "overruled": "Overruled. [pause] Creative. Incorrect. But creative.",
    "allowed": "[sigh] I'll allow it. I want to see what happens.",
    "denied": "Denied. [pause] But the court has written it down, and will think about it tonight.",
}
_RESPONDER_FALLBACK = [
    "[gasp] I — [pause] no comment. Can I say no comment? I'm saying no comment.",
    "Okay, that is *wildly* specific, and I'd like to know who told you.",
    "[pause] ...I was hoping nobody would ask that. Ever.",
]


@handler("intervention")
async def run_intervention(s: AsyncSession, job: AudioGenerationJob, progress) -> dict:
    sess = await load_session(s, job.payload["session_id"])
    iv = next(i for i in sess.interventions if i.id == job.payload["intervention_id"])
    case = await cs.load_case(s, sess.case_id)
    assert case
    ps = await cs.load_plan_script(s, case)
    assert ps
    plan, _script = ps
    scene_row = next(sc for sc in case.scenes if sc.scene_key == iv.scene_key)
    llm = get_llm(case.llm_provider)
    text = iv.free_text or ""
    await progress("intervention", {"stage": "ruling"})

    res = await llm.structured(
        system="You are the clerk of a comedy courtroom. Classify a juror's shouted intervention and decide the "
               "fair ruling. Keep it fictional. Valid responders: "
               + ", ".join(f"{c.key} ({c.name})" for c in plan.characters if c.role in ("witness", "defendant", "prosecutor", "defense")),
        prompt=f"Case: {plan.title}\nThe juror shouts: \"{text}\"",
        schema=Ruling, fallback=lambda: _classify_fallback(text, plan), temperature=0.4, effort="low", max_tokens=300,
    )
    ruling = res.value
    if not plan.character(ruling.responder):
        ruling.responder = "defendant"
    spec = SceneSpec(f"live-{iv.id}", Phase(scene_row.phase), scene_row.title, ())
    transcript = [DialogueTurn.model_validate(r.data) for r in scene_row.turns if r.branch_key is None and r.session_id is None][-8:]

    async def speak(key: str, intent: str, tid: str, fallback_text: str, kind: str) -> DialogueTurn:
        ch = plan.character(key)
        assert ch
        slot = Slot(key, intent, kind)
        ctx = TurnContext(plan=plan, case=cs.case_input(case), spec=spec, slot=slot, slot_index=0,
                          brief=SceneBrief(title=scene_row.title, goal="Respond to a juror's live intervention", line_intents=[intent]),
                          transcript=transcript)
        agent = agent_for(ch)
        out = await llm.structured(
            system=agent.system_prompt(ctx), prompt=agent.user_prompt(ctx), schema=TurnDraft,
            fallback=lambda: TurnDraft(text=fallback_text, emotion="deadpan" if key == "judge" else "nervous",
                                       delivery="dry, unimpressed" if key == "judge" else "caught off guard",
                                       intensity=3, pause_before_ms=300),
            temperature=0.9, effort="low", max_tokens=600,
        )
        turn = to_turn(out.value, ctx, ch, tid)
        return turn.model_copy(update={"sfx": ["gavel"] if key == "judge" else [], "scores": None, "points": 0})

    r = random.Random(seed_for(iv.id))
    judge = await speak("judge", f"A juror shouted: \"{text}\". Rule {ruling.ruling.upper()} (say the ruling word first) in one dry line.",
                        f"live-{iv.id}-r1", _JUDGE_FALLBACK.get(ruling.ruling, _JUDGE_FALLBACK["allowed"]), "ruling")
    transcript.append(judge)
    answer = await speak(ruling.responder, f"Respond, in character, to the juror's intervention: \"{text}\" (the judge ruled {ruling.ruling}).",
                         f"live-{iv.id}-r2", r.choice(_RESPONDER_FALLBACK), "line")

    branch = f"live-{iv.id}"
    rows = []
    for i, t in enumerate([judge, answer]):
        row = DialogueTurnRow(scene_id=scene_row.id, session_id=sess.id, turn_key=t.id, branch_key=branch, order=100 + i,
                              speaker=t.speaker, text=t.text, data=t.model_dump(mode="json"))
        s.add(row)
        rows.append(row)
    await s.flush()

    await progress("intervention", {"stage": "voicing"})
    settings = get_settings()
    svc = AudioGenerationService(get_audio_provider(settings, case.audio_provider))
    rep = await svc.prepare(s, case, rows, progress)
    audio_source = case.audio_provider
    if not rep.complete:
        # Paid audio not permitted (or failed): voice it locally and say so.
        rep = await AudioGenerationService(get_audio_provider(settings, "mock")).prepare(s, case, rows, progress)
        audio_source = "mock-fallback"
    side = ruling.favours if ruling.favours in ("prosecution", "defense") else None
    iv.status = "ready"
    iv.source = "live" if res.source != "fallback" else "fallback"
    iv.response_turn_keys = [t.id for t in (judge, answer)]
    iv.effect = {"favours": side, "points": 1 if side else 0, "ruling": ruling.ruling, "audio": audio_source}
    await s.commit()
    return {"intervention_id": iv.id, "ruling": ruling.ruling, "audio": audio_source, "llm": res.source}
