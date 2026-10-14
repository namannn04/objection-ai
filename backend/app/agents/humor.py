"""Humor evaluation. Scores are heuristic assessments against a rubric, not a
measurement of whether people will laugh. A weak scene is regenerated alone.
"""

from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel, Field

from app.domain.models import CasePlan, DialogueTurn, Scene
from app.llm.providers import LLMProvider

RUBRIC = ("originality", "relevance", "character_consistency", "timing", "freshness", "coherence", "escalation", "punchline")
PASS_THRESHOLD = 5.5


class HumorScores(BaseModel):
    originality: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)
    character_consistency: float = Field(ge=0, le=10)
    timing: float = Field(ge=0, le=10)
    freshness: float = Field(ge=0, le=10, description="10 = no repetition of earlier jokes")
    coherence: float = Field(ge=0, le=10)
    escalation: float = Field(ge=0, le=10)
    punchline: float = Field(ge=0, le=10)


class HumorReport(BaseModel):
    scene_id: str
    scores: HumorScores
    overall: float
    weakest_line: int | None = None
    notes: list[str] = Field(default_factory=list)
    source: str = "heuristic"

    @property
    def passed(self) -> bool:
        return self.overall >= PASS_THRESHOLD


_WORD = re.compile(r"[a-z']+")
_STOP = set("the a an and or of to in is it that this i you your my we be was for on with as at are not but".split())


def _content_words(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 2]


def _trigrams(text: str) -> set[tuple[str, ...]]:
    w = _content_words(text)
    return {tuple(w[i : i + 3]) for i in range(len(w) - 2)}


def heuristic(scene: Scene, plan: CasePlan, earlier: list[DialogueTurn]) -> HumorReport:
    turns = scene.turns
    notes: list[str] = []
    earlier_tri = set().union(*(_trigrams(t.subtitle) for t in earlier)) if earlier else set()
    repeats = [i for i, t in enumerate(turns) if _trigrams(t.subtitle) & earlier_tri]
    freshness = max(0.0, 10 - 3 * len(repeats))
    if repeats:
        notes.append(f"lines {repeats} reuse phrasing from earlier scenes")

    topic_words = set(_content_words(" ".join([plan.title, plan.accusation_summary, *plan.running_gags])))
    rel_hits = sum(1 for t in turns if set(_content_words(t.subtitle)) & topic_words)
    relevance = min(10.0, 4 + 6 * rel_hits / max(1, len(turns)))

    lengths = [len(t.subtitle.split()) for t in turns]
    too_long = [i for i, n in enumerate(lengths) if n > 55]
    timing = 8.0 - 2 * len(too_long) + (1.5 if any(t.performance.pause_before_ms >= 500 for t in turns) else 0)
    if too_long:
        notes.append(f"lines {too_long} are long for comic timing")

    speakers = Counter(t.speaker for t in turns)
    clash = 8.0 if len(speakers) >= 3 else 6.0
    techniques = {t.technique for t in turns if t.technique}
    originality = min(10.0, 5 + 1.2 * len(techniques))
    intens = [t.performance.intensity for t in turns]
    escalation = 8.0 if intens and intens[-1] >= intens[0] or max(intens, default=0) >= 4 else 5.5
    last = turns[-1].subtitle
    punchline = 7.5 if len(last.split()) <= 30 else 5.5
    gag_calls = sum(1 for t in turns for g in plan.running_gags if g and g.lower() in t.subtitle.lower())
    if gag_calls:
        originality = min(10.0, originality + 1)
    empty = [i for i, t in enumerate(turns) if len(t.subtitle) < 6]
    coherence = 8.5 - 3 * len(empty)

    scores = HumorScores(
        originality=originality, relevance=relevance, character_consistency=clash, timing=max(0, timing),
        freshness=freshness, coherence=max(0, coherence), escalation=escalation, punchline=punchline,
    )
    vals = [getattr(scores, k) for k in RUBRIC]
    weakest = (repeats or too_long or empty or [None])[0]
    return HumorReport(scene_id=scene.id, scores=scores, overall=round(sum(vals) / len(vals), 2), weakest_line=weakest, notes=notes)


class CriticVerdict(BaseModel):
    scores: HumorScores
    weakest_line: int = Field(ge=0)
    notes: list[str]


CRITIC_SYSTEM = """You are a comedy script editor for a courtroom comedy show. Score the scene 0-10 on each rubric
dimension. Be strict: generic jokes, repetition and lines that break character score low. Your scores are
heuristic editorial judgement, not a prediction of audience laughter."""


async def evaluate(llm: LLMProvider, scene: Scene, plan: CasePlan, earlier: list[DialogueTurn]) -> HumorReport:
    base = heuristic(scene, plan, earlier)
    if llm.name == "mock":
        return base
    lines = "\n".join(f"{i}. {t.speaker} [{t.performance.emotion}]: {t.subtitle}" for i, t in enumerate(scene.turns))
    prompt = f"Case: {plan.title}\nRunning gags: {plan.running_gags}\nScene '{scene.title}':\n{lines}"
    res = await llm.structured(
        system=CRITIC_SYSTEM, prompt=prompt, schema=CriticVerdict,
        fallback=lambda: CriticVerdict(scores=base.scores, weakest_line=base.weakest_line or 0, notes=base.notes),
        temperature=0.2, effort="low", max_tokens=800,
    )
    v = res.value
    # Blend the critic with the heuristic so a single odd critique can't sink a scene.
    blended = HumorScores(**{k: round(0.6 * getattr(v.scores, k) + 0.4 * getattr(base.scores, k), 2) for k in RUBRIC})
    vals = [getattr(blended, k) for k in RUBRIC]
    return HumorReport(scene_id=scene.id, scores=blended, overall=round(sum(vals) / len(vals), 2),
                       weakest_line=min(v.weakest_line, len(scene.turns) - 1), notes=[*base.notes, *v.notes][:6],
                       source="critic" if res.source != "fallback" else "heuristic")
