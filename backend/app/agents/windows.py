"""Intervention windows: controlled moments where the jury may act.

Options and their response branches are generated ahead of time, so choosing
one plays instantly. Free-text interventions (chaos mode) are generated live
by the InterventionService.
"""

from __future__ import annotations

import random

from pydantic import BaseModel, Field

from app.agents import scripted
from app.agents.agents import TurnContext, TurnDraft, agent_for, template_ctx, to_turn
from app.agents.blueprint import SceneSpec, Slot
from app.agents.director import CaseInput, SceneBrief, resolve_speaker
from app.agents.topic import seed_for
from app.domain.models import CasePlan, DialogueTurn, InterventionOption, InterventionWindow
from app.llm.providers import LLMProvider


class OptionDraft(BaseModel):
    label: str = Field(description="2-4 word button label")
    text: str = Field(description="What the juror shouts, one sentence, funny and specific")


class OptionsDraft(BaseModel):
    options: list[OptionDraft] = Field(description="Exactly 2 options")


_FALLBACK_OPTIONS = {
    "objection": [
        OptionDraft(label="Hearsay!", text="Objection! Hearsay — that exhibit heard it from a friend of a friend."),
        OptionDraft(label="Badgering!", text="Objection! The prosecution is badgering the defendant with vibes."),
    ],
    "question": [
        OptionDraft(label="Under oath?", text="Did you rehearse this testimony in the mirror this morning?"),
        OptionDraft(label="Whose side?", text="Whose side are you actually on here?"),
    ],
}


async def _draft_options(llm: LLMProvider, kind: str, plan: CasePlan, transcript: list[DialogueTurn]) -> list[OptionDraft]:
    recent = "\n".join(f"{t.speaker}: {t.subtitle}" for t in transcript[-6:])
    ask = {
        "objection": "two different objections a juror could shout at the last exhibit",
        "question": "two different questions a juror could put to the witness",
    }[kind]
    res = await llm.structured(
        system="You write interactive choices for a comedy courtroom show. Short, specific, funny, fictional.",
        prompt=f"Case: {plan.title}\nRecent:\n{recent}\n\nWrite {ask}.",
        schema=OptionsDraft, fallback=lambda: OptionsDraft(options=_FALLBACK_OPTIONS[kind]),
        temperature=0.9, effort="low", max_tokens=600,
    )
    opts = res.value.options[:2]
    return opts if len(opts) == 2 else _FALLBACK_OPTIONS[kind]


def _scripted_turn(table_key: str, speaker_key: str, plan: CasePlan, ci: CaseInput, spec: SceneSpec, tid: str, salt: str) -> DialogueTurn:
    speaker = plan.character(speaker_key)
    assert speaker
    slot = Slot(speaker_key, table_key, "ruling" if speaker_key == "judge" else "line")
    t = TurnContext(plan=plan, case=ci, spec=spec, slot=slot, slot_index=0,
                    brief=SceneBrief(title="", goal="", line_intents=[""]), transcript=[])
    r = random.Random(seed_for(ci.case_id, spec.key, salt))
    text, emotion, delivery, intensity, pause = scripted.pick(scripted.RESPONSES, table_key, speaker.role, template_ctx(t, speaker), r)
    sfx = ["gavel"] if speaker_key == "judge" and table_key in ("sustained", "overruled") else []
    turn = to_turn(TurnDraft(text=text, emotion=emotion, delivery=delivery, intensity=intensity, pause_before_ms=pause),
                   t, speaker, tid)
    return turn.model_copy(update={"sfx": sfx, "scores": None, "points": 0})


async def _respond(llm: LLMProvider, speaker_key: str, intent: str, plan: CasePlan, ci: CaseInput, spec: SceneSpec,
                   transcript: list[DialogueTurn], tid: str, fallback_key: str) -> DialogueTurn:
    """Generate a response line with the speaker's own agent, falling back to scripted."""
    speaker = plan.character(speaker_key)
    assert speaker
    fb = _scripted_turn(fallback_key, speaker_key, plan, ci, spec, tid, tid)
    if llm.name == "mock":
        return fb
    slot = Slot(speaker_key, intent, "ruling" if speaker_key == "judge" else "line")
    t = TurnContext(plan=plan, case=ci, spec=spec, slot=slot, slot_index=0,
                    brief=SceneBrief(title=spec.title, goal="Respond to a juror's intervention", line_intents=[intent]),
                    transcript=transcript)
    agent = agent_for(speaker)
    res = await llm.structured(system=agent.system_prompt(t), prompt=agent.user_prompt(t), schema=TurnDraft,
                               fallback=lambda: TurnDraft(text=fb.text, emotion=fb.performance.emotion,
                                                          delivery=fb.performance.delivery, intensity=3, pause_before_ms=300),
                               temperature=0.9, effort="low", max_tokens=600)
    turn = to_turn(res.value, t, speaker, tid)
    return turn.model_copy(update={"sfx": fb.sfx, "scores": None, "points": 0})


async def build_window(llm: LLMProvider, kind: str, spec: SceneSpec, plan: CasePlan, ci: CaseInput,
                       transcript: list[DialogueTurn]) -> InterventionWindow:
    pre = f"{spec.key}-w"
    if kind in ("opening_vote", "final_vote"):
        final = kind == "final_vote"
        sides = [("prosecution", "Guilty" if final else "The prosecution", "Guilty! Lock it up." if final else "The prosecution's opening hit harder."),
                 ("defense", "Not guilty" if final else "The defense", "Not guilty. Let it go." if final else "The defense's opening was smoother.")]
        options = []
        for side, label, text in sides:
            response = [] if final else [
                _scripted_turn(f"vote_ack:{side}", "judge", plan, ci, spec, f"{pre}-{side}-r1", side)
            ]
            options.append(InterventionOption(id=f"{pre}-{side}", label=label, text=text, favours=side,  # type: ignore[arg-type]
                                              points=6 if final else 2, response=response))
        prompt = "The jury must decide. Guilty, or not guilty?" if final else "Whose opening statement landed harder?"
        return InterventionWindow(kind="vote", prompt=prompt, options=options, allow_free_text=False)

    drafts = await _draft_options(llm, kind, plan, transcript)
    options = []
    if kind == "objection":
        for i, d in enumerate(drafts):
            sustained = i == 0
            oid = f"{pre}-o{i + 1}"
            ruling = await _respond(llm, "judge", f"Rule {'SUSTAINED' if sustained else 'OVERRULED'} on the juror's objection: '{d.text}'. Say the ruling word first.",
                                    plan, ci, spec, transcript, f"{oid}-r1", "sustained" if sustained else "overruled")
            retort_by, retort_key = ("prosecutor", "retort_prosecutor") if sustained else ("defense", "retort_defense")
            retort = await _respond(llm, retort_by, "React to the judge's ruling on the juror's objection in one short line.",
                                    plan, ci, spec, [*transcript, ruling], f"{oid}-r2", retort_key)
            options.append(InterventionOption(id=oid, label=d.label[:60], text=d.text[:240],
                                              favours="defense" if sustained else "prosecution",
                                              points=2 if sustained else 1, response=[ruling, retort]))
        prompt = "Something about that exhibit smells funny. Object?"
    else:
        w = resolve_speaker(Slot("witness:0", ""), spec, plan) if spec.witness is not None else plan.by_role("witness")[0]
        for i, d in enumerate(drafts):
            oid = f"{pre}-q{i + 1}"
            answer = await _respond(llm, w.key, f"Answer the juror's question honestly and embarrassingly: '{d.text}'",
                                    plan, ci, spec, transcript, f"{oid}-r1", "overruled")
            if llm.name == "mock":
                answer = answer.model_copy(update={"text": _witness_answer(i, plan, w.key), "kind": "testimony"})
            options.append(InterventionOption(id=oid, label=d.label[:60], text=d.text[:240], favours="defense", points=1,
                                              response=[answer]))
        prompt = f"Ask {w.name} something. Anything. Please."
    return InterventionWindow(kind=kind, prompt=prompt, options=options, allow_free_text=True)  # type: ignore[arg-type]


def _witness_answer(i: int, plan: CasePlan, key: str) -> str:
    return [
        "[pause] ...Yes. Twice. The second time with hand gestures. I'd like that struck from the record.",
        "[laugh] Whoever's winning? [pause] Is that not how this works? Nobody told me how this works.",
    ][i % 2]
