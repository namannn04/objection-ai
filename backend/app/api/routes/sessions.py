from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_case_or_404
from app.db import get_session
from app.models import Case
from app.schemas.api import FreeIntervention, OptionChoice, SessionCreate
from app.services import session_service as ss
from app.services.manifest import build_manifest

router = APIRouter(prefix="/api", tags=["courtroom"])


def _err(exc: ss.SessionError) -> HTTPException:
    return HTTPException(exc.status, str(exc))


async def _ctx(s: AsyncSession, session_id: str):
    try:
        sess = await ss.load_session(s, session_id)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    case = await get_case_or_404(s, sess.case_id)
    return sess, case


async def _respond(s: AsyncSession, sess, case: Case) -> dict:
    await s.commit()
    sess, case = await _ctx(s, sess.id)
    return ss.state(sess, case)


@router.post("/cases/{ref}/sessions", summary="Open a courtroom session (returns state + manifest)")
async def create_session(ref: str, body: SessionCreate, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    try:
        sess = await ss.create_session(s, case, body.mode)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    await s.commit()
    sess, case = await _ctx(s, sess.id)
    return {"state": ss.state(sess, case), "manifest": build_manifest(case)}


@router.get("/sessions/{session_id}", summary="Session state")
async def get_state(session_id: str, s: AsyncSession = Depends(get_session)):
    sess, case = await _ctx(s, session_id)
    return ss.state(sess, case)


@router.post("/sessions/{session_id}/start", summary="All rise: begin the trial")
async def start(session_id: str, s: AsyncSession = Depends(get_session)):
    sess, case = await _ctx(s, session_id)
    try:
        await ss.start(s, sess, case)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    return await _respond(s, sess, case)


@router.post("/sessions/{session_id}/scenes/{scene_key}/complete", summary="Report a scene finished playing")
async def complete(session_id: str, scene_key: str, s: AsyncSession = Depends(get_session)):
    sess, case = await _ctx(s, session_id)
    try:
        await ss.complete_scene(s, sess, case, scene_key)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    return await _respond(s, sess, case)


@router.post("/sessions/{session_id}/windows/{scene_key}/choose", summary="Choose an objection / question / vote")
async def choose(session_id: str, scene_key: str, body: OptionChoice, s: AsyncSession = Depends(get_session)):
    sess, case = await _ctx(s, session_id)
    try:
        iv = await ss.choose_option(s, sess, case, scene_key, body.option_id)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    out = await _respond(s, sess, case)
    return {"state": out, "intervention_id": iv.id, "response_turn_keys": iv.response_turn_keys}


@router.post("/sessions/{session_id}/windows/{scene_key}/intervene", summary="Chaos mode: free-text intervention")
async def intervene(session_id: str, scene_key: str, body: FreeIntervention, s: AsyncSession = Depends(get_session)):
    from app.services.intervention_service import submit_free_text

    sess, case = await _ctx(s, session_id)
    try:
        result = await submit_free_text(s, sess, case, scene_key, body.text)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    out = await _respond(s, sess, case)
    return {"state": out, **result}


@router.post("/sessions/{session_id}/windows/resolve", summary="Close the open window and resume the trial")
async def resolve(session_id: str, s: AsyncSession = Depends(get_session)):
    sess, case = await _ctx(s, session_id)
    try:
        await ss.resolve_window(s, sess, case)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    return await _respond(s, sess, case)


@router.get("/sessions/{session_id}/verdict", summary="The verdict (once reached)")
async def verdict(session_id: str, s: AsyncSession = Depends(get_session)):
    sess, case = await _ctx(s, session_id)
    if not sess.verdict:
        raise HTTPException(409, "the court has not reached a verdict yet")
    return ss.verdict_payload(sess.verdict)


@router.post("/sessions/{session_id}/replay", summary="Replay the case (alternate verdicts keep history)")
async def replay(session_id: str, body: SessionCreate, s: AsyncSession = Depends(get_session)):
    sess, case = await _ctx(s, session_id)
    try:
        new = await ss.create_session(s, case, body.mode or sess.participation_mode, parent=sess.id)
    except ss.SessionError as exc:
        raise _err(exc) from exc
    await s.commit()
    new, case = await _ctx(s, new.id)
    return {"state": ss.state(new, case), "manifest": build_manifest(case)}
