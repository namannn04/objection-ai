"""Narrative Director: casts the case, plans the arc, briefs each scene, sets pacing.

The director decides *what each line must accomplish*. It never writes other
characters' dialogue and never changes the trial phase; structure comes from
the blueprint and the state machine.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.agents import topic as topic_mod
from app.agents.blueprint import SceneSpec, Slot, blueprint, witness_count
from app.agents.cast import (
    DEFENSE,
    ENSEMBLE,
    JUDGE,
    PROSECUTOR,
    REPORTER,
    CastMemberDraft,
    DefendantDraft,
    defendant_spec,
    witness_spec,
)
from app.domain.models import (
    TRIAL_PHASES,
    CasePlan,
    CharacterSpec,
    ComedyBeat,
    DialogueTurn,
    EvidenceSpec,
    Phase,
    PhaseOutline,
)
from app.llm.providers import LLMProvider


@dataclass(slots=True)
class CaseInput:
    case_id: str
    defendant: str
    accusation: str
    context: str = ""
    language: str = "en"
    comedy_intensity: str = "unserious"
    drama_level: int = 60
    trial_length: str = "quick"
    participation_mode: str = "jury"
    case_number: str = ""


class EvidenceDraft(BaseModel):
    title: str
    description: str
    kind: str = Field(description="document | photo | log | object | recording | chart")
    favours: str = Field(description="prosecution | defense")
    strength: int = Field(ge=1, le=5)
    details: list[str] = Field(default_factory=list, description="2-4 short card bullet points")


class PlanDraft(BaseModel):
    title: str = Field(description="e.g. 'The People vs. The Office Wi-Fi'")
    accusation_summary: str
    charges: list[str] = Field(description="1-3 formal-sounding absurd charges")
    defendant: DefendantDraft
    witnesses: list[CastMemberDraft] = Field(description="1-2 witnesses relevant to the case")
    surprise_witness: CastMemberDraft
    evidence: list[EvidenceDraft] = Field(
        description="Exactly 3: two favouring prosecution, the third favouring defense and revealing the twist"
    )
    plot_twist: str = Field(description="A reveal that reframes the case without contradicting established facts")
    running_gags: list[str] = Field(description="2-3 short phrases to call back later")
    punishment_guilty: str = Field(description="Harmless, imaginative sentence, starting with 'Sentenced to'")
    acquittal_note: str = Field(description="One-line reason the court might acquit")
    leaning: str = Field(description="prosecution | defense — which side the evidence favours")


DIRECTOR_SYSTEM = """You are the Narrative Director of THE COURT OF ABSOLUTE NONSENSE, a comedy courtroom show.
Ridiculous problems are tried with the seriousness of a Supreme Court case. The humour comes from
contrast: absurd accusations, deadly serious courtroom behaviour. You plan the case, never perform it.

Rules:
- Everything is clearly fictional. Evidence is fictional case material, never presented as real fact.
- Never target, humiliate or make allegations about real private individuals. Real people named by the
  user become harmless fictional archetypes.
- Never make serious real-world tragedies the subject of jokes. Punishments are absurd and harmless.
- Prefer specific, concrete, surprising details over generic jokes. No repeated punchlines.
- Witnesses must have a clear relationship to the case, and a slip that undermines their own testimony."""


def fallback_plan_draft(ci: CaseInput) -> PlanDraft:
    p = topic_mod.analyze(ci.defendant, ci.accusation, ci.case_id)
    kind = {"tech": "object", "time": "concept", "person": "human"}.get(p.kind, p.kind)

    def member(w: topic_mod.WitnessIdea) -> CastMemberDraft:
        return CastMemberDraft(
            name=w.name, personality=w.personality, speaking_style=w.personality,
            relationship_to_case=w.relationship, knows=w.knows, slip=w.slip,
            voice_description=w.personality, pitch="mid", glyph=w.glyph, palette=w.palette,
        )

    ev = [
        EvidenceDraft(title=t, description=d, kind=k, favours=f, strength=4 if f == "prosecution" else 3,
                      details=["Fictional case material", "Entered into the record", "Handled with tweezers"])
        for t, d, k, f in p.evidence
    ]
    return PlanDraft(
        title=f"The People vs. {p.defendant}",
        accusation_summary=f"{p.defendant} stands accused of {p.crime}.",
        charges=[f"Aggravated {('inconvenience' if p.kind != 'person' else 'tardiness')}", f"Wilful {p.crime}"[:120]],
        defendant=DefendantDraft(
            name=p.defendant, kind=kind, personality=p.defendant_personality, speaking_style=p.defendant_voice,
            alibi=p.alibi, excuse=p.excuse, voice_description=p.defendant_voice, pitch="mid",
            glyph=p.glyph, palette="ember",
        ),
        witnesses=[member(w) for w in p.witnesses],
        surprise_witness=member(p.surprise),
        evidence=ev,
        plot_twist=p.twist,
        running_gags=p.gags,
        punishment_guilty=p.guilty_sentence,
        acquittal_note=p.acquittal_note,
        leaning="prosecution",
    )


def _plan_prompt(ci: CaseInput) -> str:
    return f"""Plan a new case.

Defendant (who/what is accused): {ci.defendant}
Accusation: {ci.accusation}
Extra context from the plaintiff: {ci.context or "(none)"}
Language for all dialogue: {ci.language}
Comedy intensity: {ci.comedy_intensity} (mild = restrained deadpan; unserious = silly; chaos = maximum escalation)
Drama meter: {ci.drama_level}/100
Trial length: {ci.trial_length}

Give the defendant a vivid, consistent personality that fits what it is. Cast {witness_count(ci.trial_length)} witness(es)
with a direct relationship to the accusation, plus one unexpected-but-relevant surprise witness.
Exactly 3 evidence items: 2 favour prosecution, the 3rd favours defense and supports the plot twist."""


async def plan_case(llm: LLMProvider, ci: CaseInput) -> tuple[CasePlan, str]:
    res = await llm.structured(
        system=DIRECTOR_SYSTEM, prompt=_plan_prompt(ci), schema=PlanDraft,
        fallback=lambda: fallback_plan_draft(ci), temperature=1.0, effort="medium", max_tokens=6000,
    )
    return assemble_plan(res.value, ci), res.source


def assemble_plan(d: PlanDraft, ci: CaseInput) -> CasePlan:
    """Deterministically turn a creative draft into a validated, complete plan."""
    n_w = witness_count(ci.trial_length)  # type: ignore[arg-type]
    witnesses = list(d.witnesses)[:n_w]
    fallback = fallback_plan_draft(ci)
    while len(witnesses) < n_w:
        witnesses.append(fallback.witnesses[len(witnesses) % len(fallback.witnesses)])
    chars: list[CharacterSpec] = [*ENSEMBLE, defendant_spec(d.defendant)]
    chars += [witness_spec(w, i) for i, w in enumerate(witnesses)]
    if ci.trial_length != "quick":
        chars.append(witness_spec(d.surprise_witness, 0, surprise=True))

    ev_drafts = list(d.evidence)[:3]
    while len(ev_drafts) < 3:
        ev_drafts.append(fallback.evidence[len(ev_drafts)])
    evidence = []
    for i, e in enumerate(ev_drafts):
        favours = "defense" if i == 2 else ("prosecution" if e.favours != "defense" else "defense")
        evidence.append(
            EvidenceSpec(
                id="ABC"[i], title=e.title[:120], description=e.description[:400],
                kind=e.kind if e.kind in ("document", "photo", "log", "object", "recording", "chart") else "document",
                favours=favours, strength=max(1, min(5, e.strength)), details=[x[:120] for x in e.details[:4]],
                is_twist=i == 2,
            )
        )

    specs = blueprint(ci.trial_length)  # type: ignore[arg-type]
    outline = []
    for phase in TRIAL_PHASES:
        beats = [s.title for s in specs if s.phase == phase]
        if beats:
            outline.append(PhaseOutline(phase=phase, goal=_PHASE_GOALS[phase], beats=beats,
                                        techniques=sorted({sl.technique for s in specs if s.phase == phase for sl in s.slots if sl.technique})))  # type: ignore[misc]
    gags = [g for g in d.running_gags if g][:3] or fallback.running_gags
    moments = [
        ComedyBeat(technique="callback", setup=f"'{gags[0]}' is introduced early", payoff="It returns in closing arguments", payoff_phase=Phase.CLOSING_ARGUMENTS),
        ComedyBeat(technique="contradiction", setup="The witness testifies confidently", payoff="The witness admits the embarrassing truth under cross", payoff_phase=Phase.CROSS_EXAMINATION),
        ComedyBeat(technique="absurd_punishment", setup="The charges are read with total gravity", payoff="A harmless, oddly specific sentence", payoff_phase=Phase.VERDICT),
    ]
    sentence = d.punishment_guilty.strip()
    return CasePlan(
        title=d.title[:160],
        case_number=ci.case_number or "CR-0000-000",
        accusation_summary=d.accusation_summary[:400],
        charges=[c[:140] for c in d.charges[:3]] or ["Aggravated inconvenience"],
        defendant_profile=d.defendant.personality,
        prosecutor_strategy="",
        defense_strategy="",
        characters=chars,
        evidence=evidence,
        outline=outline,
        comedic_moments=moments,
        running_gags=gags,
        plot_twist=d.plot_twist,
        punishments={"guilty": sentence, "not_guilty": d.acquittal_note.strip()},
        leaning="defense" if d.leaning == "defense" else "prosecution",
    )


_PHASE_GOALS = {
    Phase.OPENING_STATEMENTS: "Establish the absurd charge with total seriousness; introduce the defendant's personality.",
    Phase.EVIDENCE_PRESENTATION: "Escalate the accusation with fictional exhibits; first clash between counsel.",
    Phase.WITNESS_EXAMINATION: "Witness testimony that sounds damning and overshares.",
    Phase.CROSS_EXAMINATION: "The defense exposes a contradiction; surprises land here.",
    Phase.CLOSING_ARGUMENTS: "Each side calls back the best moments; the defendant gets the last word.",
    Phase.DELIBERATION: "A breath before the verdict; the reporter recaps.",
    Phase.VERDICT: "The ruling and an absurd, harmless sentence.",
}


# ── scene briefs ─────────────────────────────────────────────────────────


class SceneBrief(BaseModel):
    title: str
    goal: str
    line_intents: list[str] = Field(description="One sentence per line: what that line must accomplish")
    callback: str = Field(default="", description="A running gag to call back in this scene, if any")


_INTENT_TEXT = {
    "intro": "Welcome the audience to the show and introduce tonight's case in two dry sentences.",
    "open_court": "Open the court, read the charge gravely, express weary disdain for the case.",
    "opening_statement": "Deliver an opening statement that frames the case for your side.",
    "introduce_self": "First words in court: reveal your personality and your signature excuse.",
    "react_to_defendant": "React to the defendant with a deadpan one-liner, then keep things moving.",
    "present_evidence": "Present the exhibit dramatically and say why it is damning.",
    "excuse": "Blurt out an excuse for the exhibit.",
    "object_to_evidence": "Object to the exhibit on absurd-but-legal-sounding grounds.",
    "rule_on_objection": "Rule on the objection (overruled) with dry wit.",
    "reveal_twist": "Reveal the defense exhibit that exposes the plot twist.",
    "react_to_twist": "Lose composure at the twist.",
    "restore_order": "Restore order after the gasp.",
    "call_witness": "Call the witness and ask what they saw.",
    "testify": "Give testimony in character: your relationship to the case and what you saw.",
    "leading_question": "Ask a wildly leading question.",
    "overshare": "Agree, then overshare something nobody asked for.",
    "cross_examine": "Cross-examine the witness, steering toward their weak point.",
    "contradict_self": "Crack under pressure and admit your embarrassing slip.",
    "outraged_objection": "Object in outrage because the answer hurt your case.",
    "overrule_and_scold": "Overrule and scold counsel.",
    "call_surprise_witness": "Call the surprise witness by name.",
    "allow_surprise": "Grudgingly allow the surprise witness.",
    "surprise_testimony": "Deliver surprising but relevant testimony.",
    "react_to_surprise": "React to the surprise testimony, calling back a running gag.",
    "closing_argument": "Closing argument: call back the best moments and ask for your verdict.",
    "last_words": "Final words before deliberation.",
    "recap": "Recap the case for the audience in two sentences, wryly.",
    "deliberate": "Deliberate aloud with a long dramatic pause.",
    "verdict_guilty": "Announce the verdict: GUILTY, with ceremony.",
    "verdict_not_guilty": "Announce the verdict: NOT GUILTY, reluctantly.",
    "sentence": "Pronounce the absurd harmless sentence and adjourn.",
    "dismissal": "Explain the acquittal in one dry line and release the defendant.",
    "react_guilty": "React to being found guilty.",
    "react_acquitted": "React to being acquitted.",
    "outro": "Sign off the episode in one or two sentences.",
}


def default_brief(spec: SceneSpec, plan: CasePlan) -> SceneBrief:
    gag = plan.running_gags[0] if plan.running_gags else ""
    return SceneBrief(
        title=spec.title,
        goal=next((o.goal for o in plan.outline if o.phase == spec.phase), spec.title),
        line_intents=[_INTENT_TEXT.get(s.intent, s.intent) for s in spec.slots],
        callback=gag if any(s.technique == "callback" for s in spec.slots) else "",
    )


async def brief_scene(llm: LLMProvider, spec: SceneSpec, plan: CasePlan, transcript: list[DialogueTurn]) -> tuple[SceneBrief, str]:
    speakers = [resolve_speaker(s, spec, plan).name for s in spec.slots]
    recent = "\n".join(f"{t.speaker}: {t.subtitle}" for t in transcript[-10:]) or "(the trial has not started)"
    base = default_brief(spec, plan)
    prompt = f"""Case: {plan.title}. {plan.accusation_summary}
Running gags: {", ".join(plan.running_gags)}. Plot twist (secret until revealed): {plan.plot_twist}
Recent transcript:
{recent}

Brief the scene "{spec.title}" ({spec.phase.value}). Speakers in order: {", ".join(speakers)}.
Default intents: {base.line_intents}
Write exactly {len(spec.slots)} line_intents, sharpened for THIS case: specific, escalating, no repeated jokes."""
    res = await llm.structured(system=DIRECTOR_SYSTEM, prompt=prompt, schema=SceneBrief,
                               fallback=lambda: base, temperature=0.8, effort="low", max_tokens=1500)
    brief = res.value
    if len(brief.line_intents) != len(spec.slots):
        return base, "fallback"
    return brief, res.source


def resolve_speaker(slot: Slot, spec: SceneSpec, plan: CasePlan) -> CharacterSpec:
    if slot.who.startswith("witness:"):
        idx = int(slot.who.split(":")[1])
        ws = [c for c in plan.characters if c.role == "witness" and not c.surprise]
        return ws[min(idx, len(ws) - 1)]
    if slot.who == "surprise":
        return next((c for c in plan.characters if c.surprise), plan.by_role("witness")[0])
    return plan.character(slot.who) or {"judge": JUDGE, "prosecutor": PROSECUTOR, "defense": DEFENSE, "reporter": REPORTER}[slot.who]
