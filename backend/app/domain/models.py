"""Structured courtroom domain: plans, characters, scripts, interventions.

Everything an agent produces is validated against these models before it is
persisted, voiced, or shown. The LLM never writes free-form state.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Phase(StrEnum):
    CASE_CREATED = "CASE_CREATED"
    CASE_PREPARATION = "CASE_PREPARATION"
    SCRIPT_PLANNING = "SCRIPT_PLANNING"
    SCRIPT_VALIDATION = "SCRIPT_VALIDATION"
    AUDIO_PREPARATION = "AUDIO_PREPARATION"
    COURTROOM_READY = "COURTROOM_READY"
    OPENING_STATEMENTS = "OPENING_STATEMENTS"
    EVIDENCE_PRESENTATION = "EVIDENCE_PRESENTATION"
    WITNESS_EXAMINATION = "WITNESS_EXAMINATION"
    CROSS_EXAMINATION = "CROSS_EXAMINATION"
    PLAYER_INTERVENTION = "PLAYER_INTERVENTION"
    CLOSING_ARGUMENTS = "CLOSING_ARGUMENTS"
    DELIBERATION = "DELIBERATION"
    VERDICT = "VERDICT"
    CASE_COMPLETED = "CASE_COMPLETED"
    FAILED = "FAILED"


TRIAL_PHASES: tuple[Phase, ...] = (
    Phase.OPENING_STATEMENTS,
    Phase.EVIDENCE_PRESENTATION,
    Phase.WITNESS_EXAMINATION,
    Phase.CROSS_EXAMINATION,
    Phase.CLOSING_ARGUMENTS,
    Phase.DELIBERATION,
    Phase.VERDICT,
)

Role = Literal["judge", "prosecutor", "defense", "defendant", "witness", "reporter"]
Side = Literal["prosecution", "defense"]
ComedyIntensity = Literal["mild", "unserious", "chaos"]
TrialLength = Literal["quick", "standard", "full"]
ParticipationMode = Literal["spectator", "jury", "chaos"]

Emotion = Literal[
    "neutral", "serious", "stern", "angry", "smug", "sarcastic", "desperate",
    "shocked", "confused", "amused", "sad", "proud", "nervous", "triumphant",
    "deadpan", "dramatic", "whispering", "exasperated",
]
Reaction = Literal["gasp", "facepalm", "smirk", "angry", "confused", "laugh", "shocked", "nod", "sweat"]
Sfx = Literal["gavel", "objection", "crowd_gasp", "crowd_laugh", "crowd_murmur", "dramatic_sting"]
TurnKind = Literal[
    "line", "objection", "ruling", "evidence", "testimony", "question",
    "verdict", "sentence", "aside", "recap",
]
HumorTechnique = Literal[
    "deadpan", "escalation", "callback", "contradiction", "unexpected_witness",
    "personality_clash", "dramatic_irony", "absurd_punishment",
    "controlled_interruption", "awkward_silence",
]

# Inline performance cues authors may embed in dialogue text: "[sigh] Fine."
# The audio compiler maps these to provider syntax; subtitles strip them.
CUE_TAGS: frozenset[str] = frozenset(
    {"pause", "long pause", "laugh", "chuckle", "sigh", "gasp", "whisper", "clears throat", "sobs", "scoff"}
)
_TAG_RE = re.compile(r"\[([^\[\]]{1,24})\]")
_EMPH_RE = re.compile(r"\*([^*]+)\*")


def clean_cues(text: str) -> str:
    """Drop unsupported bracket tags, keep supported ones, normalise whitespace."""

    def keep(m: re.Match[str]) -> str:
        tag = m.group(1).strip().lower()
        return f"[{tag}]" if tag in CUE_TAGS else ""

    return re.sub(r"\s{2,}", " ", _TAG_RE.sub(keep, text)).strip()


def subtitle_text(text: str) -> str:
    """Spoken words only: no cue tags, no emphasis markers."""
    out = _EMPH_RE.sub(r"\1", _TAG_RE.sub("", text))
    return re.sub(r"\s{2,}", " ", out).strip()


class VoiceSpec(BaseModel):
    archetype: str = Field(description="Casting archetype, e.g. 'deep authoritative judge'")
    description: str = Field(description="How the voice sounds, in a sentence")
    pitch: Literal["low", "mid", "high"] = "mid"
    pace: Literal["slow", "measured", "fast"] = "measured"


class VisualSpec(BaseModel):
    kind: Literal["human", "object", "concept"] = "human"
    glyph: str = Field(default="", max_length=6, description="Short mark on an object/concept face, e.g. 'JS'")
    palette: Literal["gold", "burgundy", "ivory", "teal", "violet", "ember", "slate", "moss"] = "slate"
    accessory: Literal["wig", "glasses", "tie", "bowtie", "headset", "monocle", "none"] = "none"


class CharacterSpec(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,40}$")
    role: Role
    name: str = Field(min_length=1, max_length=60)
    title: str = Field(default="", max_length=80)
    personality: str
    speaking_style: str
    objective: str
    private_knowledge: list[str] = Field(default_factory=list, description="Facts only this agent knows")
    bias: str = ""
    weakness: str = Field(default="", description="A contradiction or soft spot others can exploit")
    relationship_to_case: str = ""
    voice: VoiceSpec
    visual: VisualSpec = Field(default_factory=VisualSpec)
    surprise: bool = False


class EvidenceSpec(BaseModel):
    id: str = Field(pattern=r"^[A-Z]$")
    title: str
    description: str
    kind: Literal["document", "photo", "log", "object", "recording", "chart"] = "document"
    favours: Side = "prosecution"
    strength: int = Field(ge=1, le=5, default=3)
    details: list[str] = Field(default_factory=list, max_length=6)
    is_twist: bool = False


class PhaseOutline(BaseModel):
    phase: Phase
    goal: str
    beats: list[str] = Field(min_length=1, max_length=8)
    techniques: list[HumorTechnique] = Field(default_factory=list)


class ComedyBeat(BaseModel):
    technique: HumorTechnique
    setup: str
    payoff: str
    payoff_phase: Phase


class CasePlan(BaseModel):
    title: str
    case_number: str
    accusation_summary: str
    charges: list[str] = Field(min_length=1, max_length=4)
    defendant_profile: str
    prosecutor_strategy: str
    defense_strategy: str
    characters: list[CharacterSpec] = Field(min_length=5, max_length=9)
    evidence: list[EvidenceSpec] = Field(min_length=2, max_length=6)
    outline: list[PhaseOutline]
    comedic_moments: list[ComedyBeat] = Field(default_factory=list)
    running_gags: list[str] = Field(default_factory=list)
    plot_twist: str = ""
    punishments: dict[Literal["guilty", "not_guilty"], str]
    leaning: Side = Field(default="prosecution", description="Which side the evidence favours before jury input")

    def character(self, key: str) -> CharacterSpec | None:
        return next((c for c in self.characters if c.key == key), None)

    def by_role(self, role: Role) -> list[CharacterSpec]:
        return [c for c in self.characters if c.role == role]


class Performance(BaseModel):
    emotion: Emotion = "neutral"
    delivery: str = Field(default="", max_length=160, description="Natural-language acting direction")
    intensity: int = Field(default=3, ge=1, le=5)
    pause_before_ms: int = Field(default=0, ge=0, le=3000)


class DialogueTurn(BaseModel):
    id: str
    speaker: str
    text: str = Field(min_length=1, max_length=600)
    kind: TurnKind = "line"
    performance: Performance = Field(default_factory=Performance)
    addressed_to: str | None = None
    evidence_id: str | None = None
    reactions: dict[str, Reaction] = Field(default_factory=dict)
    sfx: list[Sfx] = Field(default_factory=list)
    technique: HumorTechnique | None = None
    scores: Side | None = Field(default=None, description="Which side this line scores for, if any")
    points: int = Field(default=0, ge=0, le=3)

    @field_validator("text")
    @classmethod
    def _cues(cls, v: str) -> str:
        return clean_cues(v)

    @property
    def subtitle(self) -> str:
        return subtitle_text(self.text)


class InterventionOption(BaseModel):
    id: str
    label: str = Field(max_length=60)
    text: str = Field(max_length=240, description="What the user's objection/question says")
    favours: Side | None = None
    points: int = Field(default=2, ge=0, le=6)
    response: list[DialogueTurn] = Field(default_factory=list, description="Pre-generated branch")


class InterventionWindow(BaseModel):
    kind: Literal["objection", "question", "vote"]
    prompt: str
    options: list[InterventionOption] = Field(min_length=2, max_length=4)
    allow_free_text: bool = True


class Scene(BaseModel):
    id: str
    phase: Phase
    title: str
    strategy: Literal["line", "scene"] = "line"
    turns: list[DialogueTurn] = Field(min_length=1)
    window: InterventionWindow | None = None
    branch: Literal["verdict_guilty", "verdict_not_guilty"] | None = None


class TrialScript(BaseModel):
    scenes: list[Scene]

    def main_scenes(self) -> list[Scene]:
        return [s for s in self.scenes if s.branch is None]

    def verdict_scene(self, guilty: bool) -> Scene | None:
        key = "verdict_guilty" if guilty else "verdict_not_guilty"
        return next((s for s in self.scenes if s.branch == key), None)

    def all_turns(self) -> list[DialogueTurn]:
        out: list[DialogueTurn] = []
        for s in self.scenes:
            out.extend(s.turns)
            if s.window:
                for o in s.window.options:
                    out.extend(o.response)
        return out
