"""Trial structure. The Narrative Director picks a blueprint by trial length; the
LLM fills in content, never structure. Slots name *who* speaks and *what the
line must accomplish*; agents decide *how*.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.models import Phase, TrialLength


@dataclass(frozen=True, slots=True)
class Slot:
    who: str  # judge | prosecutor | defense | defendant | reporter | witness:0 | witness:1 | surprise
    intent: str
    kind: str = "line"
    technique: str | None = None
    evidence: int | None = None  # index into plan.evidence


@dataclass(frozen=True, slots=True)
class SceneSpec:
    key: str
    phase: Phase
    title: str
    slots: tuple[Slot, ...]
    window: str | None = None  # opening_vote | objection | question | final_vote
    witness: int | None = None
    branch: str | None = None
    strategy: str = "line"
    tags: tuple[str, ...] = field(default_factory=tuple)


S = Slot
P = Phase

OPENING = SceneSpec(
    "s01", P.OPENING_STATEMENTS, "All Rise",
    (
        S("reporter", "intro", "recap"),
        S("judge", "open_court", "line", "deadpan"),
        S("prosecutor", "opening_statement", "line", "escalation"),
        S("defense", "opening_statement", "line", "personality_clash"),
        S("defendant", "introduce_self", "line", "deadpan"),
        S("judge", "react_to_defendant", "ruling", "awkward_silence"),
    ),
    window="opening_vote",
)

EVIDENCE_A = SceneSpec(
    "s02", P.EVIDENCE_PRESENTATION, "Exhibit A",
    (
        S("prosecutor", "present_evidence", "evidence", "escalation", evidence=0),
        S("defendant", "excuse", "line", "deadpan"),
        S("defense", "object_to_evidence", "objection", "controlled_interruption", evidence=0),
        S("judge", "rule_on_objection", "ruling", "deadpan"),
    ),
    window="objection",
)

EVIDENCE_B = SceneSpec(
    "s03", P.EVIDENCE_PRESENTATION, "The Plot Thickens",
    (
        S("prosecutor", "present_evidence", "evidence", "escalation", evidence=1),
        S("defense", "reveal_twist", "evidence", "dramatic_irony", evidence=2),
        S("prosecutor", "react_to_twist", "line", "personality_clash"),
        S("judge", "restore_order", "ruling", "deadpan"),
    ),
    tags=("twist",),
)

def _witness_exam(key: str, idx: int, title: str) -> SceneSpec:
    who = f"witness:{idx}"
    return SceneSpec(
        key, P.WITNESS_EXAMINATION, title,
        (
            S("prosecutor", "call_witness", "question"),
            S(who, "testify", "testimony", "deadpan"),
            S("prosecutor", "leading_question", "question", "escalation"),
            S(who, "overshare", "testimony", "dramatic_irony"),
        ),
        witness=idx,
    )


def _cross(key: str, idx: int, title: str, window: str | None = "question") -> SceneSpec:
    who = f"witness:{idx}"
    return SceneSpec(
        key, P.CROSS_EXAMINATION, title,
        (
            S("defense", "cross_examine", "question", "contradiction"),
            S(who, "contradict_self", "testimony", "contradiction"),
            S("prosecutor", "outraged_objection", "objection", "controlled_interruption"),
            S("judge", "overrule_and_scold", "ruling", "deadpan"),
        ),
        window=window,
        witness=idx,
    )


SURPRISE = SceneSpec(
    "s07", P.CROSS_EXAMINATION, "A Surprise Witness",
    (
        S("defense", "call_surprise_witness", "question", "unexpected_witness"),
        S("judge", "allow_surprise", "ruling", "deadpan"),
        S("surprise", "surprise_testimony", "testimony", "unexpected_witness"),
        S("defendant", "react_to_surprise", "line", "callback"),
    ),
    tags=("surprise",),
)

CLOSING = SceneSpec(
    "s08", P.CLOSING_ARGUMENTS, "Closing Arguments",
    (
        S("prosecutor", "closing_argument", "line", "callback"),
        S("defense", "closing_argument", "line", "callback"),
        S("defendant", "last_words", "line", "awkward_silence"),
    ),
    window="final_vote",
)

DELIBERATION = SceneSpec(
    "s09", P.DELIBERATION, "Deliberation",
    (
        S("reporter", "recap", "recap"),
        S("judge", "deliberate", "line", "awkward_silence"),
    ),
)


def _verdict(guilty: bool) -> SceneSpec:
    return SceneSpec(
        "v_guilty" if guilty else "v_not_guilty",
        P.VERDICT,
        "The Verdict",
        (
            S("judge", "verdict_guilty" if guilty else "verdict_not_guilty", "verdict"),
            S("judge", "sentence" if guilty else "dismissal", "sentence", "absurd_punishment"),
            S("defendant", "react_guilty" if guilty else "react_acquitted", "line", "callback"),
            S("reporter", "outro", "recap"),
        ),
        branch="verdict_guilty" if guilty else "verdict_not_guilty",
    )


VERDICT_GUILTY = _verdict(True)
VERDICT_NOT_GUILTY = _verdict(False)


def blueprint(length: TrialLength) -> list[SceneSpec]:
    if length == "quick":
        main = [OPENING, EVIDENCE_A, _witness_exam("s04", 0, "The Witness"), _cross("s05", 0, "Cross-Examination"), CLOSING, DELIBERATION]
    elif length == "standard":
        main = [
            OPENING, EVIDENCE_A, EVIDENCE_B,
            _witness_exam("s04", 0, "The Witness"), _cross("s05", 0, "Cross-Examination"),
            SURPRISE, CLOSING, DELIBERATION,
        ]
    else:
        main = [
            OPENING, EVIDENCE_A, EVIDENCE_B,
            _witness_exam("s04", 0, "The First Witness"), _cross("s05", 0, "Cross-Examination", window=None),
            _witness_exam("s06", 1, "The Second Witness"), _cross("s06b", 1, "Cross-Examination, Again"),
            SURPRISE, CLOSING, DELIBERATION,
        ]
    return [*main, VERDICT_GUILTY, VERDICT_NOT_GUILTY]


def witness_count(length: TrialLength) -> int:
    return 2 if length == "full" else 1
