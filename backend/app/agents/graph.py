"""Courtroom orchestration graph (LangGraph).

plan → strategize → [brief → perform → evaluate → (retry once | accept)]* → windows → validate

Each scene is briefed by the Narrative Director, then performed turn by turn
by the speaking agents, then scored by the humor evaluator. A weak scene is
regenerated alone (at most once). Phase structure comes from the blueprint;
agents only write content.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.agents.agents import TurnContext, agent_for
from app.agents.blueprint import SceneSpec, blueprint
from app.agents.director import DIRECTOR_SYSTEM, CaseInput, brief_scene, plan_case, resolve_speaker
from app.agents.humor import HumorReport, evaluate
from app.agents.windows import build_window
from app.domain.models import CasePlan, DialogueTurn, Scene, TrialScript
from app.domain.validation import ValidationReport, validate_script
from app.llm.providers import LLMProvider

Progress = Callable[[str, dict[str, Any]], Awaitable[None]]

MAX_SCENE_RETRIES = 1


class Strategy(BaseModel):
    strategy: str = Field(description="Two-sentence private game plan")


class TrialState(TypedDict, total=False):
    case: CaseInput
    plan: CasePlan
    specs: list[SceneSpec]
    idx: int
    attempt: int
    scenes: list[Scene]
    transcript: list[DialogueTurn]
    reports: list[dict]
    sources: Counter
    pending: Scene | None
    pending_report: HumorReport | None
    script: TrialScript
    validation: ValidationReport
    used_templates: set


async def _noop(_: str, __: dict[str, Any]) -> None:
    return None


def build_graph(llm: LLMProvider, progress: Progress = _noop):
    async def plan_node(state: TrialState) -> TrialState:
        ci = state["case"]
        await progress("planning", {"message": "Finding lawyers willing to defend this nonsense."})
        plan, source = await plan_case(llm, ci)
        specs = blueprint(ci.trial_length)  # type: ignore[arg-type]
        await progress("planned", {"title": plan.title, "source": source, "scenes": len(specs)})
        return {"plan": plan, "specs": specs, "idx": 0, "attempt": 0, "scenes": [], "transcript": [],
                "reports": [], "sources": Counter({source: 1}), "used_templates": set()}

    async def strategize_node(state: TrialState) -> TrialState:
        plan = state["plan"]
        defendant_name = plan.character("defendant").name  # type: ignore[union-attr]
        await progress("strategizing", {"message": "Both lawyers are pretending to have read the file."})

        async def strat(role: str, fb: str) -> tuple[str, str]:
            c = plan.character(role)
            assert c
            twist = f"\nYou privately know: {plan.plot_twist}" if role == "defense" else ""
            res = await llm.structured(
                system=f"You are {c.name}, {c.role}. {c.personality}{twist}",
                prompt=f"Case: {plan.title}. {plan.accusation_summary}\nEvidence: "
                + "; ".join(f"{e.id}: {e.title}" for e in plan.evidence if role == "defense" or not e.is_twist)
                + "\nWrite your private two-sentence strategy.",
                schema=Strategy, fallback=lambda: Strategy(strategy=fb), temperature=0.8, effort="low", max_tokens=400,
            )
            return res.value.strategy, res.source

        (p, ps), (d, ds) = await asyncio.gather(
            strat("prosecutor", f"Treat {defendant_name} as a career criminal. "
                  "Lead with the strongest exhibit and make the witness cry."),
            strat("defense", "Paint the client as misunderstood, then reveal the twist at the perfect moment and "
                  "turn the prosecution's own witness."),
        )
        plan = plan.model_copy(update={"prosecutor_strategy": p, "defense_strategy": d})
        src = state["sources"]
        src.update([ps, ds])
        return {"plan": plan, "sources": src}

    async def scene_node(state: TrialState) -> TrialState:
        plan, ci = state["plan"], state["case"]
        spec = state["specs"][state["idx"]]
        transcript = list(state["transcript"])
        await progress("scene", {"index": state["idx"], "total": len(state["specs"]), "title": spec.title,
                                 "attempt": state["attempt"]})
        brief, bsrc = await brief_scene(llm, spec, plan, transcript)
        src = state["sources"]
        src.update([bsrc])
        turns: list[DialogueTurn] = []
        used = state.setdefault("used_templates", set())  # type: ignore[typeddict-item]
        witness = resolve_speaker(_witness_slot(spec), spec, plan) if spec.witness is not None else None
        for i, slot in enumerate(spec.slots):
            speaker = resolve_speaker(slot, spec, plan)
            ev = plan.evidence[slot.evidence] if slot.evidence is not None and slot.evidence < len(plan.evidence) else None
            strategy = plan.prosecutor_strategy if speaker.role == "prosecutor" else plan.defense_strategy if speaker.role == "defense" else ""
            ctx = TurnContext(plan=plan, case=ci, spec=spec, slot=slot, slot_index=i, brief=brief,
                              transcript=[*transcript, *turns], strategy=strategy,
                              witness=witness if slot.who != "surprise" else speaker, evidence=ev,
                              extra={"used_templates": used})
            turn, tsrc = await agent_for(speaker).speak(llm, ctx, f"{spec.key}-t{i + 1:02d}")
            src.update([tsrc])
            turns.append(turn)
            await progress("line", {"scene": spec.key, "speaker": speaker.name, "text": turn.subtitle, "source": tsrc})
        scene = Scene(id=spec.key, phase=spec.phase, title=brief.title or spec.title, strategy=spec.strategy,  # type: ignore[arg-type]
                      turns=turns, branch=spec.branch)  # type: ignore[arg-type]
        earlier = [t for s in state["scenes"] for t in s.turns]
        report = await evaluate(llm, scene, plan, earlier)
        return {"pending": scene, "pending_report": report, "sources": src}

    def judge_scene(state: TrialState) -> str:
        report = state["pending_report"]
        assert report is not None
        if not report.passed and state["attempt"] < MAX_SCENE_RETRIES and llm.name != "mock":
            return "retry"
        return "accept"

    async def retry_node(state: TrialState) -> TrialState:
        await progress("regenerating", {"scene": state["specs"][state["idx"]].key,
                                        "score": state["pending_report"].overall if state["pending_report"] else None})
        return {"attempt": state["attempt"] + 1}

    async def accept_node(state: TrialState) -> TrialState:
        scene, report = state["pending"], state["pending_report"]
        assert scene and report
        transcript = state["transcript"] if scene.branch else [*state["transcript"], *scene.turns]
        reports = [*state["reports"], {**report.model_dump(), "attempts": state["attempt"] + 1}]
        await progress("scene_done", {"scene": scene.id, "humor": report.overall})
        return {"scenes": [*state["scenes"], scene], "transcript": transcript, "reports": reports,
                "idx": state["idx"] + 1, "attempt": 0, "pending": None, "pending_report": None}

    def more_scenes(state: TrialState) -> str:
        return "scene" if state["idx"] < len(state["specs"]) else "windows"

    async def windows_node(state: TrialState) -> TrialState:
        plan, ci = state["plan"], state["case"]
        await progress("windows", {"message": "Preparing objections the jury is legally allowed to shout."})
        specs = {s.key: s for s in state["specs"]}
        scenes = list(state["scenes"])

        async def build(i: int, sc: Scene):
            spec = specs[sc.id]
            if not spec.window:
                return i, None
            upto = [t for s in scenes[: i + 1] if not s.branch for t in s.turns]
            return i, await build_window(llm, spec.window, spec, plan, ci, upto)

        for i, window in await asyncio.gather(*(build(i, s) for i, s in enumerate(scenes))):
            if window:
                scenes[i] = scenes[i].model_copy(update={"window": window})
        return {"scenes": scenes}

    async def validate_node(state: TrialState) -> TrialState:
        script = TrialScript(scenes=state["scenes"])
        report = validate_script(state["plan"], script)
        await progress("validated", {"valid": report.valid, "errors": report.errors[:5], **report.stats})
        return {"script": script, "validation": report}

    g = StateGraph(TrialState)
    g.add_node("plan", plan_node)
    g.add_node("strategize", strategize_node)
    g.add_node("scene", scene_node)
    g.add_node("retry", retry_node)
    g.add_node("accept", accept_node)
    g.add_node("windows", windows_node)
    g.add_node("validate", validate_node)
    g.set_entry_point("plan")
    g.add_edge("plan", "strategize")
    g.add_edge("strategize", "scene")
    g.add_conditional_edges("scene", judge_scene, {"retry": "retry", "accept": "accept"})
    g.add_edge("retry", "scene")
    g.add_conditional_edges("accept", more_scenes, {"scene": "scene", "windows": "windows"})
    g.add_edge("windows", "validate")
    g.add_edge("validate", END)
    return g.compile()


def _witness_slot(spec: SceneSpec):
    from app.agents.blueprint import Slot

    return Slot(f"witness:{spec.witness}", "")


async def generate_trial(llm: LLMProvider, ci: CaseInput, progress: Progress = _noop) -> TrialState:
    graph = build_graph(llm, progress)
    return await graph.ainvoke({"case": ci}, {"recursion_limit": 200})  # type: ignore[return-value]


__all__ = ["generate_trial", "build_graph", "DIRECTOR_SYSTEM"]
