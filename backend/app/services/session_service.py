"""Courtroom sessions: server-authoritative progress through the trial.

The client plays prepared audio and reports when a scene finishes; the server
validates the report, applies the legal phase transition, opens intervention
windows, records jury input, and computes the verdict from the record.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import CasePlan, DialogueTurn, Phase
from app.domain.state_machine import IllegalTransition, TransitionContext, transition
from app.models import Case, CourtroomSession, JuryVote, Objection, SceneRow, UserIntervention, Verdict


class SessionError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


async def load_session(s: AsyncSession, session_id: str) -> CourtroomSession:
    q = select(CourtroomSession).where(CourtroomSession.id == session_id).options(
        selectinload(CourtroomSession.interventions), selectinload(CourtroomSession.votes),
        selectinload(CourtroomSession.verdict),
    )
    sess = (await s.execute(q)).scalar_one_or_none()
    if not sess:
        raise SessionError("session not found", 404)
    return sess


def main_scenes(case: Case) -> list[SceneRow]:
    return [sc for sc in case.scenes if sc.branch is None]


def _ctx(case: Case, **kw) -> TransitionContext:
    return TransitionContext(roles_present=frozenset(c.role for c in case.characters),
                             evidence_count=len(case.evidence), **kw)


def _move(sess: CourtroomSession, case: Case, target: str, **kw) -> None:
    try:
        new = transition(sess.phase, target, _ctx(case, **kw))
    except IllegalTransition as exc:
        raise SessionError(str(exc)) from exc
    sess.phase_history = [*sess.phase_history, {"from": sess.phase, "to": new.value, "at": datetime.now(UTC).isoformat()}]
    sess.phase = new.value


async def create_session(s: AsyncSession, case: Case, mode: str | None, parent: str | None = None) -> CourtroomSession:
    if case.status != Phase.COURTROOM_READY.value:
        raise SessionError(f"case is not ready for trial (status {case.status})")
    sess = CourtroomSession(case_id=case.id, case_version=case.current_version,
                            participation_mode=mode or case.participation_mode, phase=Phase.COURTROOM_READY.value,
                            cursor_scene=0, phase_history=[], parent_session_id=parent)
    s.add(sess)
    await s.flush()
    return sess


def state(sess: CourtroomSession, case: Case) -> dict:
    scenes = main_scenes(case)
    nxt = scenes[sess.cursor_scene].scene_key if sess.cursor_scene < len(scenes) else None
    verdict = sess.verdict
    return {
        "session_id": sess.id, "phase": sess.phase, "mode": sess.participation_mode,
        "cursor": sess.cursor_scene, "next_scene": nxt, "open_window": sess.open_window_scene,
        "verdict_scene": ("v_guilty" if verdict.guilty else "v_not_guilty") if verdict else None,
        "verdict": verdict_payload(verdict) if verdict else None,
        "history": sess.phase_history,
        "votes": [{"scene": v.scene_key, "choice": v.choice} for v in sess.votes],
        "interventions": [{"id": i.id, "scene": i.scene_key, "kind": i.kind, "option_id": i.option_id,
                           "free_text": i.free_text, "status": i.status, "source": i.source,
                           "response_turn_keys": i.response_turn_keys} for i in sess.interventions],
    }


async def start(s: AsyncSession, sess: CourtroomSession, case: Case) -> None:
    if sess.phase != Phase.COURTROOM_READY.value:
        raise SessionError("trial already started")
    _move(sess, case, Phase.OPENING_STATEMENTS.value)


def _windows_enabled(sess: CourtroomSession) -> bool:
    return sess.participation_mode in ("jury", "chaos")


async def complete_scene(s: AsyncSession, sess: CourtroomSession, case: Case, scene_key: str) -> None:
    """The client finished playing `scene_key`."""
    scenes = main_scenes(case)
    if sess.phase == Phase.VERDICT.value:
        expected = "v_guilty" if sess.verdict and sess.verdict.guilty else "v_not_guilty"
        if scene_key != expected:
            raise SessionError(f"expected verdict scene {expected}")
        _move(sess, case, Phase.CASE_COMPLETED.value)
        sess.completed_at = datetime.now(UTC)
        return
    if sess.open_window_scene:
        raise SessionError("an intervention window is open; resolve or skip it first")
    if sess.cursor_scene >= len(scenes) or scenes[sess.cursor_scene].scene_key != scene_key:
        raise SessionError(f"out-of-order scene report: expected {scenes[sess.cursor_scene].scene_key if sess.cursor_scene < len(scenes) else 'none'}")
    current = scenes[sess.cursor_scene]
    sess.cursor_scene += 1
    if current.window and _windows_enabled(sess):
        sess.open_window_scene = current.scene_key
        _move(sess, case, Phase.PLAYER_INTERVENTION.value, window_open=True)
        return
    await _enter_next(s, sess, case)


async def _enter_next(s: AsyncSession, sess: CourtroomSession, case: Case) -> None:
    scenes = main_scenes(case)
    if sess.cursor_scene < len(scenes):
        target = scenes[sess.cursor_scene].phase
        if target != sess.phase:
            _move(sess, case, target)
        return
    # Main trial finished (deliberation played): reach the verdict.
    verdict = await compute_verdict(s, sess, case)
    _move(sess, case, Phase.VERDICT.value, verdict_ready=verdict is not None)


async def resolve_window(s: AsyncSession, sess: CourtroomSession, case: Case) -> None:
    """Close the open window (after its response played, or when skipped)."""
    if not sess.open_window_scene:
        raise SessionError("no intervention window is open")
    sess.open_window_scene = None
    scenes = main_scenes(case)
    if sess.cursor_scene < len(scenes):
        _move(sess, case, scenes[sess.cursor_scene].phase)
    else:  # defensive: the last main scene had a window
        _move(sess, case, Phase.DELIBERATION.value)
        await _enter_next(s, sess, case)


def _scene(case: Case, key: str) -> SceneRow:
    sc = next((x for x in case.scenes if x.scene_key == key), None)
    if not sc:
        raise SessionError("unknown scene", 404)
    return sc


async def choose_option(s: AsyncSession, sess: CourtroomSession, case: Case, scene_key: str, option_id: str) -> UserIntervention:
    if sess.open_window_scene != scene_key:
        raise SessionError("that window is not open")
    if any(i.scene_key == scene_key and i.status != "rejected" for i in sess.interventions):
        raise SessionError("the jury already spoke in this window", 429)
    sc = _scene(case, scene_key)
    window = sc.window or {}
    opt = next((o for o in window.get("options", []) if o["id"] == option_id), None)
    if not opt:
        raise SessionError("unknown option", 404)
    kind = window.get("kind", "objection")
    response_keys = [r.turn_key for r in sc.turns if r.branch_key == option_id]
    iv = UserIntervention(session_id=sess.id, scene_key=scene_key, kind=kind, option_id=option_id,
                          status="ready", response_turn_keys=response_keys,
                          effect={"favours": opt.get("favours"), "points": opt.get("points", 0)}, source="pregenerated")
    s.add(iv)
    sess.interventions.append(iv)
    await s.flush()
    if kind == "vote":
        weight = int(opt.get("points", 2))
        vote = JuryVote(session_id=sess.id, scene_key=scene_key, choice=opt.get("favours") or "prosecution", weight=weight)
        s.add(vote)
        sess.votes.append(vote)
    elif kind == "objection":
        first = next((r for r in sc.turns if r.branch_key == option_id), None)
        ruling = "sustained" if first and "sustained" in first.text.lower()[:60] else "overruled"
        s.add(Objection(session_id=sess.id, intervention_id=iv.id, grounds=opt["text"], ruling=ruling))
    return iv


# ── verdict ────────────────────────────────────────────────────────────────


def score_record(case: Case, plan: CasePlan, sess: CourtroomSession) -> dict:
    """Deterministic scoring from the trial record. The judge's verdict follows it."""
    board = {"prosecution": 0.0, "defense": 0.0}
    lines: list[dict] = []
    for sc in main_scenes(case):
        for r in sc.turns:
            if r.branch_key or r.session_id:
                continue
            t = DialogueTurn.model_validate(r.data)
            if t.scores and t.points:
                board[t.scores] += t.points
                lines.append({"source": "argument", "turn": t.id, "side": t.scores, "points": t.points})
    for e in plan.evidence:
        pts = e.strength / 2
        board[e.favours] += pts
        lines.append({"source": "evidence", "exhibit": e.id, "side": e.favours, "points": pts})
    lean = 1.0 if plan.leaning == "prosecution" else -1.0
    board["prosecution" if lean > 0 else "defense"] += 1
    lines.append({"source": "plan_leaning", "side": plan.leaning, "points": 1})
    for iv in sess.interventions:
        side, pts = iv.effect.get("favours"), float(iv.effect.get("points", 0))
        if side in board and iv.kind != "vote" and iv.status in ("ready", "fallback"):
            board[side] += pts
            lines.append({"source": f"jury_{iv.kind}", "scene": iv.scene_key, "side": side, "points": pts})
    for v in sess.votes:
        board[v.choice] += v.weight
        lines.append({"source": "jury_vote", "scene": v.scene_key, "side": v.choice, "points": v.weight})
    return {"board": board, "lines": lines}


def simulated_jury(board: dict, seed: str) -> dict:
    """11 simulated jurors lean with the record; the user is the 12th."""
    import random

    p, d = board["prosecution"], board["defense"]
    share = p / (p + d) if p + d else 0.5
    rnd = random.Random(seed)
    guilty = sum(1 for _ in range(11) if rnd.random() < share)
    return {"guilty": guilty, "not_guilty": 11 - guilty, "simulated": 11}


async def compute_verdict(s: AsyncSession, sess: CourtroomSession, case: Case) -> Verdict:
    if sess.verdict:
        return sess.verdict
    from app.services.case_service import load_plan_script

    ps = await load_plan_script(s, case)
    if not ps:
        raise SessionError("case has no script")
    plan, _ = ps
    rec = score_record(case, plan, sess)
    board = rec["board"]
    guilty = board["prosecution"] > board["defense"] or (board["prosecution"] == board["defense"] and plan.leaning == "prosecution")
    final_vote = next((v for v in sess.votes if v.weight >= 6), None)
    jury = simulated_jury(board, sess.id)
    if final_vote:
        jury["guilty" if final_vote.choice == "prosecution" else "not_guilty"] += 1
    charge = plan.charges[0] if plan.charges else "aggravated inconvenience"
    headline = f"GUILTY OF {charge.upper()}" if guilty else "NOT GUILTY. RELUCTANTLY."
    reasoning = (
        f"The prosecution scored {board['prosecution']:g} to the defense's {board['defense']:g} on the record"
        + (", with the jury's vote weighing heavily" if final_vote else "")
        + "."
    )
    v = Verdict(session_id=sess.id, guilty=guilty, headline=headline[:200], reasoning=reasoning,
                sentence=plan.punishments["guilty" if guilty else "not_guilty"],
                scoreboard={**rec, "jury": jury}, highlights=highlights(case))
    s.add(v)
    sess.verdict = v
    await s.flush()
    return v


def highlights(case: Case) -> dict:
    turns = [(sc, r, DialogueTurn.model_validate(r.data)) for sc in case.scenes for r in sc.turns
             if r.session_id is None and r.branch_key is None]
    def best(pred, key):
        cands = [(sc, r, t) for sc, r, t in turns if pred(sc, t)]
        if not cands:
            return None
        sc, r, t = max(cands, key=key)
        return {"turn_key": r.turn_key, "speaker": r.speaker, "text": t.subtitle, "scene": sc.scene_key}
    humor = lambda x: (x[0].humor_score or 0, x[2].performance.intensity)  # noqa: E731
    return {
        "funniest_objection": best(lambda sc, t: t.kind == "objection", humor),
        "best_comeback": best(lambda sc, t: t.kind == "ruling", humor),
        "most_dramatic": best(lambda sc, t: True, lambda x: (x[2].performance.intensity, len(x[2].subtitle))),
        "most_unexpected": best(lambda sc, t: t.technique in ("unexpected_witness", "contradiction", "dramatic_irony"), humor),
    }


def verdict_payload(v: Verdict) -> dict:
    return {"guilty": v.guilty, "headline": v.headline, "reasoning": v.reasoning, "sentence": v.sentence,
            "scoreboard": v.scoreboard, "highlights": v.highlights}
