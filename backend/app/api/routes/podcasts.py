from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_case_or_404
from app.db import get_session
from app.domain.models import Phase
from app.models import Case, PodcastEpisode
from app.schemas.api import PodcastCreate
from app.services.podcast_service import episode_payload, list_episodes, request_episode

router = APIRouter(prefix="/api", tags=["podcast"])


@router.post("/cases/{ref}/podcast", summary="Export the trial as a podcast episode")
async def create_podcast(ref: str, body: PodcastCreate, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    if case.status != Phase.COURTROOM_READY.value:
        raise HTTPException(409, "the trial audio is not ready yet")
    try:
        ep, job_id = await request_episode(s, case, body.verdict, body.session_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    await s.commit()
    return {"id": ep.id, "job_id": job_id, "status": ep.status}


@router.get("/cases/{ref}/podcasts", summary="Episode history for a case")
async def case_podcasts(ref: str, s: AsyncSession = Depends(get_session)):
    case = await get_case_or_404(s, ref)
    return [episode_payload(e, case.slug) for e in await list_episodes(s, case.id)]


@router.get("/podcasts/{episode_id}", summary="One episode")
async def get_podcast(episode_id: str, s: AsyncSession = Depends(get_session)):
    ep = await s.get(PodcastEpisode, episode_id)
    if not ep:
        raise HTTPException(404, "episode not found")
    case = await s.get(Case, ep.case_id)
    return episode_payload(ep, case.slug)
