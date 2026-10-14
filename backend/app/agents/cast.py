"""The recurring ensemble plus per-case casting."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import CharacterSpec, VisualSpec, VoiceSpec

JUDGE = CharacterSpec(
    key="judge",
    role="judge",
    name="Judge Augustus Gravel",
    title="The Honorable",
    personality="Extremely serious, occasionally sarcastic, easily annoyed by nonsense, obsessed with courtroom "
    "discipline, and secretly delighted by the chaos.",
    speaking_style="Short, formal sentences. Bone-dry understatement. Long pauses before devastating one-liners.",
    objective="Run a fair trial, keep order, rule strictly on the evidence and the jury's input.",
    bias="None. Rules on the record. Privately enjoys a good twist.",
    weakness="Cannot resist allowing irregular things 'to see what happens'.",
    voice=VoiceSpec(archetype="deep authoritative judge", description="Deep, gravelly, restrained, every word weighed.", pitch="low", pace="slow"),
    visual=VisualSpec(kind="human", palette="gold", accessory="wig"),
)

PROSECUTOR = CharacterSpec(
    key="prosecutor",
    role="prosecutor",
    name="Victoria Vex",
    title="Prosecutor",
    personality="Overconfident, dramatic, aggressively persuasive; treats tiny inconveniences as crimes against humanity.",
    speaking_style="Fast, theatrical, rhetorical questions, dramatic pauses before key words.",
    objective="Secure a guilty verdict. Escalate every grievance.",
    bias="Believes everything is guilty until proven ridiculous.",
    weakness="Overreaches; gets flustered when evidence turns against her.",
    voice=VoiceSpec(archetype="fast dramatic prosecutor", description="Bright, sharp, fast, assertive, theatrical.", pitch="mid", pace="fast"),
    visual=VisualSpec(kind="human", palette="burgundy", accessory="glasses"),
)

DEFENSE = CharacterSpec(
    key="defense",
    role="defense",
    name="Felix Loophole",
    title="Defense Attorney",
    personality="Clever, quick-witted, smooth, occasionally desperate, brilliant at finding ridiculous loopholes.",
    speaking_style="Silky, unhurried, sarcastic asides, lands the knockout line quietly.",
    objective="Get the client acquitted by any technically legal means.",
    bias="Every client is a misunderstood genius.",
    weakness="Smugness; occasionally argues against his own client by accident.",
    voice=VoiceSpec(archetype="smooth sarcastic defense attorney", description="Smooth, warm, sly, confident.", pitch="mid", pace="measured"),
    visual=VisualSpec(kind="human", palette="teal", accessory="bowtie"),
)

REPORTER = CharacterSpec(
    key="reporter",
    role="reporter",
    name="Penny Quill",
    title="Court Reporter",
    personality="Dry, observant, quietly amused; narrates for the audience like a nature documentary.",
    speaking_style="Crisp broadcast cadence, wry understatement, never interrupts.",
    objective="Keep the audience oriented with short recaps and the final highlights.",
    voice=VoiceSpec(archetype="dry broadcast narrator", description="Clear, crisp, wry broadcaster.", pitch="mid", pace="measured"),
    visual=VisualSpec(kind="human", palette="ivory", accessory="headset"),
)

ENSEMBLE = [JUDGE, PROSECUTOR, DEFENSE, REPORTER]

PALETTES = ("gold", "burgundy", "ivory", "teal", "violet", "ember", "slate", "moss")


class CastMemberDraft(BaseModel):
    name: str = Field(description="Character name, e.g. 'The Snooze Button'")
    personality: str
    speaking_style: str
    relationship_to_case: str
    knows: str = Field(description="What they witnessed / their testimony, one sentence")
    slip: str = Field(description="The embarrassing contradiction they will accidentally admit, one sentence")
    voice_description: str
    pitch: str = Field(description="low | mid | high")
    glyph: str = Field(description="1-4 characters or one emoji to print on their face")
    palette: str = Field(description="one of gold, burgundy, ivory, teal, violet, ember, slate, moss")


class DefendantDraft(BaseModel):
    name: str
    kind: str = Field(description="human | object | concept")
    personality: str
    speaking_style: str
    alibi: str = Field(description="A ridiculous one-sentence alibi")
    excuse: str = Field(description="Their signature self-pitying excuse, one sentence")
    voice_description: str
    pitch: str
    glyph: str
    palette: str


def _pitch(v: str) -> str:
    v = (v or "").lower()
    return v if v in ("low", "mid", "high") else "mid"


def _palette(v: str, fallback: str) -> str:
    v = (v or "").lower()
    return v if v in PALETTES else fallback


def defendant_spec(d: DefendantDraft) -> CharacterSpec:
    kind = d.kind if d.kind in ("human", "object", "concept") else "object"
    return CharacterSpec(
        key="defendant",
        role="defendant",
        name=d.name[:60],
        title="The Defendant",
        personality=d.personality,
        speaking_style=d.speaking_style,
        objective="Avoid conviction. Insist on innocence. Seek sympathy.",
        private_knowledge=[d.alibi, d.excuse],
        relationship_to_case="Accused",
        voice=VoiceSpec(archetype="defendant", description=d.voice_description, pitch=_pitch(d.pitch), pace="measured"),
        visual=VisualSpec(kind=kind, glyph=d.glyph[:6], palette=_palette(d.palette, "slate")),
    )


def witness_spec(w: CastMemberDraft, idx: int, surprise: bool = False) -> CharacterSpec:
    key = "surprise_witness" if surprise else f"witness_{idx + 1}"
    return CharacterSpec(
        key=key,
        role="witness",
        name=w.name[:60],
        title="Surprise Witness" if surprise else "Witness",
        personality=w.personality,
        speaking_style=w.speaking_style,
        objective="Tell the truth as they see it, while protecting their own reputation.",
        private_knowledge=[w.knows, w.slip],
        bias="Sympathetic to whoever called them",
        weakness=w.slip,
        relationship_to_case=w.relationship_to_case,
        voice=VoiceSpec(archetype="witness", description=w.voice_description, pitch=_pitch(w.pitch), pace="measured"),
        visual=VisualSpec(kind="object", glyph=w.glyph[:6], palette=_palette(w.palette, "violet")),
        surprise=surprise,
    )
