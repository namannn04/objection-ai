"""PodcastExportService: a whole trial as one mixed episode (MP3 + WAV),
with chapter markers and a timed transcript.

Order: intro sting → main trial (scene by scene, with the jury's recorded
choices for the chosen session, or none) → chosen verdict branch → outro.
Uses the same timing rules as the courtroom player, so SFX land identically.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio import ffmpeg
from app.config import get_settings
from app.domain.models import DialogueTurn
from app.models import AudioGenerationJob, CourtroomSession, PodcastEpisode
from app.services import case_service as cs
from app.services.audio_generation import ensure_sfx_fixtures
from app.services.jobs import enqueue, handler
from app.utils_phase import PHASE_TITLES

LEAD = {"objection": 0.62, "gavel": 0.5, "dramatic_sting": 0.95, "crowd_murmur": 0.15}
SFX_GAIN = {"gavel": 0.75, "objection": 0.7, "crowd_gasp": 0.45, "crowd_laugh": 0.4, "crowd_murmur": 0.35, "dramatic_sting": 0.55}


async def request_episode(s: AsyncSession, case, verdict: str | None, session_id: str | None) -> tuple[PodcastEpisode, str]:
    if session_id:
        sess = await s.get(CourtroomSession, session_id)
        if not sess or sess.case_id != case.id:
            raise ValueError("session does not belong to this case")
    ep = PodcastEpisode(case_id=case.id, session_id=session_id, title=case.title, status="queued",
                        chapters=[], transcript=[])
    s.add(ep)
    await s.flush()
    job = await enqueue(s, "export_podcast", case.id, {"episode_id": ep.id, "verdict": verdict, "session_id": session_id})
    return ep, job.id


@handler("export_podcast")
async def export_podcast(s: AsyncSession, job: AudioGenerationJob, progress) -> dict:
    ep = await s.get(PodcastEpisode, job.payload["episode_id"])
    assert ep
    case = await cs.load_case(s, ep.case_id)
    assert case
    sfx = ensure_sfx_fixtures()
    names = {c.key: c.name for c in case.characters}

    guilty = job.payload.get("verdict")
    chosen: dict[str, str] = {}
    if ep.session_id:
        from app.services.session_service import load_session

        sess = await load_session(s, ep.session_id)
        if sess.verdict and guilty is None:
            guilty = "guilty" if sess.verdict.guilty else "not_guilty"
        chosen = {i.scene_key: (i.option_id or f"live-{i.id}") for i in sess.interventions if i.status in ("ready", "fallback")}
    if guilty is None:
        ps = await cs.load_plan_script(s, case)
        guilty = "guilty" if ps and ps[0].leaning == "prosecution" else "not_guilty"

    scenes = [sc for sc in case.scenes if sc.branch is None] + [
        sc for sc in case.scenes if sc.branch == ("verdict_guilty" if guilty == "guilty" else "verdict_not_guilty")
    ]
    items: list[tuple[Path, int, float]] = []
    chapters: list[dict] = []
    transcript: list[dict] = []
    cursor = 0.0
    items.append((sfx["dramatic_sting"], 0, 0.6))
    items.append((sfx["gavel"], 1100, 0.75))
    cursor = 2.0
    for sc in scenes:
        rows = [r for r in sc.turns if r.branch_key is None and r.session_id is None]
        if sc.scene_key in chosen:
            rows += [r for r in sc.turns if r.branch_key == chosen[sc.scene_key] and r.session_id in (None, ep.session_id)]
        chapters.append({"title": sc.title, "phase": PHASE_TITLES.get(sc.phase, sc.phase), "start_ms": round(cursor * 1000)})
        cursor += 0.6
        for r in rows:
            if not r.audio:
                continue
            t = DialogueTurn.model_validate(r.data)
            cursor += 0.22 + t.performance.pause_before_ms / 1000
            lead = 0.0
            for fx in t.sfx:
                if fx in LEAD and not (fx == "gavel" and t.kind in ("verdict", "sentence")):
                    items.append((sfx[fx], round(cursor * 1000), SFX_GAIN[fx]))
                    lead = max(lead, LEAD[fx])
            start = cursor + lead
            dur = r.audio.duration_ms / 1000
            items.append((Path(r.audio.path), round(start * 1000), 1.0))
            end = start + dur
            tail = 0.0
            for fx in t.sfx:
                if fx in ("crowd_gasp", "crowd_laugh") or (fx == "gavel" and t.kind in ("verdict", "sentence")):
                    items.append((sfx[fx], round((end - 0.12) * 1000), SFX_GAIN[fx]))
                    tail = max(tail, 0.9 if fx == "crowd_laugh" else 0.55)
            transcript.append({"turn_key": r.turn_key, "speaker": r.speaker, "name": names.get(r.speaker, r.speaker),
                               "text": t.subtitle, "start_ms": round(start * 1000), "end_ms": round(end * 1000)})
            cursor = end + tail
    items.append((sfx["gavel"], round((cursor + 0.4) * 1000), 0.75))
    total_ms = round((cursor + 2.2) * 1000)

    out_dir = get_settings().export_dir / case.slug
    mp3, wav = out_dir / f"{ep.id}.mp3", out_dir / f"{ep.id}.wav"
    await progress("podcast", {"stage": "mixing", "tracks": len(items)})
    await ffmpeg.mix_timeline(items, mp3, total_ms, "mp3")
    await progress("podcast", {"stage": "mastering wav"})
    await ffmpeg.mix_timeline(items, wav, total_ms, "wav")
    ep.mp3_path, ep.wav_path = str(mp3), str(wav)
    ep.duration_ms = ffmpeg.probe_duration_ms(mp3)
    ep.chapters, ep.transcript = chapters, transcript
    ep.title = f"{case.title} — {'Guilty' if guilty == 'guilty' else 'Not Guilty'}"
    ep.status = "ready"
    await s.commit()
    return {"episode_id": ep.id, "duration_ms": ep.duration_ms}


def episode_payload(ep: PodcastEpisode, slug: str) -> dict:
    def url(p: str | None) -> str | None:
        return f"/media/exports/{slug}/{Path(p).name}" if p else None

    verdict = "guilty" if "— Guilty" in ep.title else "not_guilty" if "— Not Guilty" in ep.title else None
    return {"id": ep.id, "case_id": ep.case_id, "title": ep.title, "status": ep.status, "mp3_url": url(ep.mp3_path),
            "wav_url": url(ep.wav_path), "duration_ms": ep.duration_ms, "chapters": ep.chapters,
            "transcript": ep.transcript, "verdict": verdict, "created_at": ep.created_at}


async def list_episodes(s: AsyncSession, case_id: str) -> list[PodcastEpisode]:
    q = select(PodcastEpisode).where(PodcastEpisode.case_id == case_id).order_by(PodcastEpisode.created_at.desc())
    return list((await s.execute(q)).scalars())
