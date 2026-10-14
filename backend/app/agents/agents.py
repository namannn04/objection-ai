"""Role agents. Each has its own persona, private knowledge, objectives and
allowed line kinds. An agent sees only the public transcript plus its own
private context — the prosecutor never learns the defense's twist early.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.agents import scripted
from app.agents.blueprint import SceneSpec, Slot
from app.agents.director import CaseInput, SceneBrief
from app.agents.topic import seed_for, third_person
from app.domain.models import (
    CasePlan,
    CharacterSpec,
    DialogueTurn,
    EvidenceSpec,
    Performance,
)
from app.llm.providers import LLMProvider

ALLOWED_KINDS: dict[str, set[str]] = {
    "judge": {"line", "ruling", "verdict", "sentence", "question"},
    "prosecutor": {"line", "objection", "evidence", "question"},
    "defense": {"line", "objection", "evidence", "question"},
    "defendant": {"line", "aside"},
    "witness": {"testimony", "line"},
    "reporter": {"recap", "line"},
}

SFX_BY_KIND = {"objection": ["objection"], "verdict": ["gavel"], "sentence": ["gavel"]}

EMOTIONS = (
    "neutral serious stern angry smug sarcastic desperate shocked confused amused sad proud nervous "
    "triumphant deadpan dramatic whispering exasperated"
).split()
REACTIONS = "gasp facepalm smirk angry confused laugh shocked nod sweat".split()


class ReactionDraft(BaseModel):
    character: str = Field(description="character key of someone else present")
    reaction: str = Field(description="gasp | facepalm | smirk | angry | confused | laugh | shocked | nod | sweat")


class TurnDraft(BaseModel):
    text: str = Field(description="1-3 spoken sentences, max ~45 words. May include cues like [pause] [sigh] [laugh] "
                      "[gasp] [chuckle] [long pause] [clears throat] [scoff] and *emphasis* on one key word.")
    emotion: str = Field(description=" | ".join(EMOTIONS))
    delivery: str = Field(description="Short acting direction for the voice actor, e.g. 'icy, slow, barely contained'")
    intensity: int = Field(ge=1, le=5)
    pause_before_ms: int = Field(ge=0, le=2500, description="Comic timing pause before the line")
    reactions: list[ReactionDraft] = Field(default_factory=list, description="0-2 visible reactions from others")
    scores_for: str | None = Field(default=None, description="prosecution | defense | null — does this line win a point?")
    points: int = Field(default=0, ge=0, le=3)


AGENT_RULES = """Stay completely in character. You speak ONE line in a live comedy courtroom performance.
- The humour comes from treating absurdity with total seriousness. Commit to the bit.
- Be specific to this case. Never repeat a joke already in the transcript. Short beats land harder.
- Everything is fictional. No real private individuals, no slurs, no cruelty, no real tragedies.
- Only use these audio cues: [pause] [long pause] [sigh] [laugh] [chuckle] [gasp] [clears throat] [scoff] [whisper] [sobs].
- Wrap at most one word in *asterisks* for vocal emphasis.
- Write only spoken words plus cues. No stage directions in prose, no speaker names."""


@dataclass(slots=True)
class TurnContext:
    plan: CasePlan
    case: CaseInput
    spec: SceneSpec
    slot: Slot
    slot_index: int
    brief: SceneBrief
    transcript: list[DialogueTurn]
    strategy: str = ""
    witness: CharacterSpec | None = None
    evidence: EvidenceSpec | None = None
    extra: dict = field(default_factory=dict)


def template_ctx(t: TurnContext, speaker: CharacterSpec) -> dict:
    plan = t.plan
    defendant = plan.character("defendant")
    w = t.witness or next((c for c in plan.characters if c.role == "witness" and not c.surprise), None)
    s = next((c for c in plan.characters if c.surprise), None)
    ev = t.evidence or plan.evidence[0]
    gags = plan.running_gags + ["", "", ""]
    wk = w.private_knowledge if w else ["", ""]
    sk = s.private_knowledge if s else ["", ""]
    dk = defendant.private_knowledge if defendant else ["", ""]
    twist = plan.plot_twist.strip()
    dname = defendant.name if defendant else "The defendant"
    cap = lambda x: x[:1].upper() + x[1:] if x else x  # noqa: E731
    return {
        "D": dname,
        "d": _mid(dname),
        "w": _mid(w.name) if w else "the witness",
        "W_voc": w.name.removeprefix("The ").removeprefix("A ") if w else "witness",
        "Gag0": cap(gags[0]),
        "Gag1": cap(gags[1] or gags[0]),
        "crime": third_person(t.case.accusation),
        "case_number": plan.case_number,
        "alibi": dk[0] if dk else "",
        "excuse": dk[1] if len(dk) > 1 else "",
        "defendant_voice": defendant.voice.description.rstrip(".").lower() if defendant else "",
        "W": w.name if w else "the witness",
        "w_relationship": (w.relationship_to_case if w else "").rstrip(".") + "." if w and w.relationship_to_case else "",
        "w_knows": wk[0] if wk else "",
        "w_slip": wk[1] if len(wk) > 1 else "",
        "w_slip_lower": (wk[1][:1].lower() + wk[1][1:]) if len(wk) > 1 and wk[1] else "",
        "witness_voice": (t.witness or w).voice.description.rstrip(".").lower() if (t.witness or w) else "",
        "S": s.name if s else "a surprise witness",
        "s_relationship": s.relationship_to_case if s else "",
        "s_knows": sk[0] if sk else "",
        "s_slip": sk[1] if len(sk) > 1 else "",
        "surprise_voice": s.voice.description.rstrip(".").lower() if s else "",
        "ev_id": ev.id,
        "ev_title": ev.title.rstrip("."),
        "ev_desc": ev.description,
        "twist": twist,
        "twist_short": twist,
        "gag0": gags[0],
        "gag1": gags[1] or gags[0],
        "sentence_lower": (plan.punishments["guilty"][:1].lower() + plan.punishments["guilty"][1:]).rstrip(".") + ".",
        "acquittal": plan.punishments["not_guilty"],
    }


def _mid(name: str) -> str:
    """'The Office Wi-Fi' → 'the Office Wi-Fi' for use mid-sentence."""
    return "the " + name[4:] if name.startswith("The ") else name


class RoleAgent:
    role: str = "line"
    temperature = 0.95

    def __init__(self, character: CharacterSpec):
        self.character = character

    def system_prompt(self, t: TurnContext) -> str:
        c = self.character
        private = "\n".join(f"- {k}" for k in c.private_knowledge) or "- (nothing beyond the public record)"
        strategy = f"\nYour private strategy: {t.strategy}" if t.strategy else ""
        return f"""You are {c.title + ' ' if c.title else ''}{c.name}, the {c.role} in THE COURT OF ABSOLUTE NONSENSE.
Personality: {c.personality}
Speaking style: {c.speaking_style}
Objective: {c.objective}
Bias: {c.bias or 'none'}
Private knowledge (only you know this; reveal only when the scene calls for it):
{private}{strategy}
Language: {t.case.language}. Comedy intensity: {t.case.comedy_intensity}. Drama meter: {t.case.drama_level}/100.

{AGENT_RULES}
{self.role_rules()}"""

    def role_rules(self) -> str:
        return ""

    def user_prompt(self, t: TurnContext) -> str:
        plan = t.plan
        public_ev = "\n".join(
            f"- Exhibit {e.id}: {e.title} — {e.description}" for e in plan.evidence if not e.is_twist or self.knows_twist(t)
        )
        transcript = "\n".join(f"{x.speaker}: {x.subtitle}" for x in t.transcript[-14:]) or "(nothing yet)"
        present = ", ".join(f"{c.key} ({c.name})" for c in plan.characters if c.key != self.character.key)
        focus = ""
        if t.evidence:
            focus += f"\nThis line concerns Exhibit {t.evidence.id}: {t.evidence.title} — {t.evidence.description}"
        if t.witness and t.witness.key != self.character.key:
            focus += f"\nThe witness on the stand: {t.witness.name} ({t.witness.relationship_to_case})"
        gag = f"\nCall back this running gag if it fits: '{t.brief.callback}'" if t.brief.callback else ""
        return f"""CASE: {plan.title} — {plan.accusation_summary}
Charges: {"; ".join(plan.charges)}
Evidence on the record:
{public_ev}
Others present: {present}

TRANSCRIPT SO FAR:
{transcript}

SCENE: {t.brief.title} — {t.brief.goal}
YOUR LINE MUST: {t.brief.line_intents[t.slot_index]}{focus}{gag}

Write your single line now."""

    def knows_twist(self, t: TurnContext) -> bool:
        return False

    def fallback(self, t: TurnContext) -> TurnDraft:
        r = rng_for(t)
        used = t.extra.setdefault("used_templates", set())
        text, emotion, delivery, intensity, pause = scripted.pick(
            scripted.LINES, t.slot.intent, self.character.role, template_ctx(t, self.character), r, used
        )
        return TurnDraft(text=text, emotion=emotion, delivery=delivery, intensity=intensity,
                         pause_before_ms=pause, reactions=default_reactions(t, self.character), points=0)

    async def speak(self, llm: LLMProvider, t: TurnContext, turn_id: str) -> tuple[DialogueTurn, str]:
        res = await llm.structured(
            system=self.system_prompt(t), prompt=self.user_prompt(t), schema=TurnDraft,
            fallback=lambda: self.fallback(t), temperature=self.temperature, effort="low", max_tokens=800,
        )
        return to_turn(res.value, t, self.character, turn_id), res.source


class JudgeAgent(RoleAgent):
    role = "judge"
    temperature = 0.8

    def role_rules(self) -> str:
        return ("You manage order and rule on objections strictly by the record. You never take sides before the "
                "verdict. Your verdict follows the court's scoring, not your mood. Your humour is deadpan understatement.")


class ProsecutorAgent(RoleAgent):
    role = "prosecutor"

    def role_rules(self) -> str:
        return "You argue for conviction. You may present evidence, question witnesses, object, and escalate."


class DefenseAgent(RoleAgent):
    role = "defense"

    def knows_twist(self, t: TurnContext) -> bool:
        return True

    def system_prompt(self, t: TurnContext) -> str:
        return super().system_prompt(t) + f"\nPrivately, you have uncovered this: {t.plan.plot_twist}"

    def role_rules(self) -> str:
        return "You defend the accused. You may object, cross-examine, introduce alternative explanations, and find loopholes."


class DefendantAgent(RoleAgent):
    role = "defendant"

    def role_rules(self) -> str:
        return "You are the accused. Stay true to what you are (object, concept or person). Speak only for yourself."


class WitnessAgent(RoleAgent):
    role = "witness"

    def role_rules(self) -> str:
        return ("You answer questions only. Under cross-examination you eventually admit your embarrassing slip. "
                "Never invent facts that contradict the record.")


class ReporterAgent(RoleAgent):
    role = "reporter"
    temperature = 0.7

    def role_rules(self) -> str:
        return "You speak to the audience, never to the court. Short, wry recaps only. Never interrupt."


AGENT_TYPES: dict[str, type[RoleAgent]] = {
    "judge": JudgeAgent,
    "prosecutor": ProsecutorAgent,
    "defense": DefenseAgent,
    "defendant": DefendantAgent,
    "witness": WitnessAgent,
    "reporter": ReporterAgent,
}


def agent_for(character: CharacterSpec) -> RoleAgent:
    return AGENT_TYPES[character.role](character)


def rng_for(t: TurnContext) -> random.Random:
    return random.Random(seed_for(t.case.case_id, t.case.defendant, t.case.accusation, t.spec.key, str(t.slot_index), t.slot.intent))


def default_reactions(t: TurnContext, speaker: CharacterSpec) -> list[ReactionDraft]:
    kind_map = {
        "objection": [("judge", "facepalm")],
        "evidence": [("defendant", "sweat"), ("defense", "facepalm")],
        "verdict": [("prosecutor", "nod"), ("defense", "shocked")],
        "testimony": [("defendant", "sweat")],
    }
    if t.slot.intent in ("reveal_twist", "contradict_self", "surprise_testimony"):
        return [ReactionDraft(character="prosecutor", reaction="shocked"), ReactionDraft(character="judge", reaction="gasp")]
    if t.slot.intent == "react_to_defendant":
        return [ReactionDraft(character="prosecutor", reaction="smirk")]
    if t.slot.intent == "overshare":
        return [ReactionDraft(character="judge", reaction="confused")]
    return [ReactionDraft(character=c, reaction=r) for c, r in kind_map.get(t.slot.kind, []) if c != speaker.key]


_SCORING: dict[str, tuple[str, int]] = {
    "present_evidence": ("prosecution", 2),
    "reveal_twist": ("defense", 3),
    "testify": ("prosecution", 1),
    "contradict_self": ("defense", 2),
    "surprise_testimony": ("defense", 1),
    "closing_argument:prosecutor": ("prosecution", 1),
    "closing_argument:defense": ("defense", 1),
    "object_to_evidence": ("defense", 0),
}


def to_turn(d: TurnDraft, t: TurnContext, speaker: CharacterSpec, turn_id: str) -> DialogueTurn:
    present = {c.key for c in t.plan.characters}
    reactions = {
        r.character: r.reaction for r in d.reactions[:2]
        if r.character in present and r.character != speaker.key and r.reaction in REACTIONS
    }
    kind = t.slot.kind if t.slot.kind in ALLOWED_KINDS[speaker.role] else "line"
    sfx = list(SFX_BY_KIND.get(kind, []))
    if t.slot.intent in ("reveal_twist", "contradict_self"):
        sfx += ["crowd_gasp"]
    if t.slot.intent == "call_surprise_witness":
        sfx += ["dramatic_sting", "crowd_murmur"]
    if t.slot.intent in ("restore_order", "open_court", "overrule_and_scold"):
        sfx += ["gavel"]
    if t.slot.intent in ("react_acquitted", "outro"):
        sfx += ["crowd_laugh"] if t.slot.intent == "outro" else []
    # Scores are assigned by the director's rules, not by the speaking agent.
    scores, points = _SCORING.get(f"{t.slot.intent}:{speaker.role}") or _SCORING.get(t.slot.intent) or (None, 0)
    drama = t.case.drama_level
    intensity = max(1, min(5, round(d.intensity + (drama - 50) / 40)))
    emotion = d.emotion if d.emotion in EMOTIONS else "neutral"
    return DialogueTurn(
        id=turn_id,
        speaker=speaker.key,
        text=d.text.strip().strip('"'),
        kind=kind,  # type: ignore[arg-type]
        performance=Performance(
            emotion=emotion,  # type: ignore[arg-type]
            delivery=d.delivery[:160],
            intensity=intensity,
            pause_before_ms=max(0, min(3000, int(d.pause_before_ms * (0.6 + drama / 125)))),
        ),
        addressed_to=None,
        evidence_id=t.evidence.id if t.evidence and kind == "evidence" else None,
        reactions=reactions,  # type: ignore[arg-type]
        sfx=list(dict.fromkeys(sfx)),  # type: ignore[arg-type]
        technique=t.slot.technique,  # type: ignore[arg-type]
        scores=scores,  # type: ignore[arg-type]
        points=points,
    )
