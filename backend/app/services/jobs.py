"""DB-backed job queue. Jobs are rows in `audio_generation_jobs`; workers claim
them with SELECT … FOR UPDATE SKIP LOCKED, so several workers are safe."""

from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_factory
from app.models import AudioGenerationJob
from app.services.events import bus

log = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, AudioGenerationJob, Callable[[str, dict], Awaitable[None]]], Awaitable[dict]]
HANDLERS: dict[str, Handler] = {}


def handler(kind: str):
    def deco(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn

    return deco


async def enqueue(session: AsyncSession, kind: str, case_id: str | None, payload: dict | None = None) -> AudioGenerationJob:
    job = AudioGenerationJob(kind=kind, case_id=case_id, payload=payload or {}, status="queued")
    session.add(job)
    await session.flush()
    return job


async def _claim() -> str | None:
    async with session_factory()() as s:
        q = (select(AudioGenerationJob).where(AudioGenerationJob.status == "queued")
             .order_by(AudioGenerationJob.created_at).limit(1).with_for_update(skip_locked=True))
        job = (await s.execute(q)).scalar_one_or_none()
        if not job:
            return None
        job.status, job.started_at, job.attempts = "running", datetime.now(UTC), job.attempts + 1
        await s.commit()
        return job.id


async def run_job(job_id: str) -> None:
    async with session_factory()() as s:
        job = await s.get(AudioGenerationJob, job_id)
        assert job
        channel = f"case:{job.case_id}" if job.case_id else f"job:{job.id}"

        async def progress(event: str, data: dict) -> None:
            job.progress = {"event": event, **data}
            await bus.publish(channel, event, {"job_id": job.id, "kind": job.kind, **data})

        try:
            result = await HANDLERS[job.kind](s, job, progress)
            job.status = result.pop("_status", "done")
            job.result = result
            job.finished_at = datetime.now(UTC)
            await s.commit()
            await bus.publish(channel, "job_" + job.status, {"job_id": job.id, "kind": job.kind, **result})
        except Exception as exc:  # noqa: BLE001
            log.error("job %s failed: %s", job_id, traceback.format_exc())
            await s.rollback()
            await s.execute(update(AudioGenerationJob).where(AudioGenerationJob.id == job_id).values(
                status="failed", error=str(exc)[:1000], finished_at=datetime.now(UTC)))
            await s.commit()
            await bus.publish(channel, "job_failed", {"job_id": job_id, "kind": job.kind, "error": str(exc)[:300]})
            fail = FAIL_HOOKS.get(job.kind)
            if fail:
                await fail(job_id, str(exc))


FAIL_HOOKS: dict[str, Callable[[str, str], Awaitable[None]]] = {}


async def recover_stale(minutes: int = 15) -> None:
    """Jobs left `running` by a crashed worker are marked failed, never silently re-run
    (a re-run could repeat billable synthesis)."""
    async with session_factory()() as s:
        cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
        await s.execute(update(AudioGenerationJob).where(AudioGenerationJob.status == "running",
                                                         AudioGenerationJob.started_at < cutoff)
                        .values(status="failed", error="worker stopped while running; not retried automatically"))
        await s.commit()


async def worker_loop(stop: asyncio.Event, concurrency: int = 2) -> None:
    import app.services.intervention_service  # noqa: F401
    import app.services.podcast_service  # noqa: F401  (registers handlers)
    import app.services.pipeline  # noqa: F401

    await recover_stale()
    running: set[asyncio.Task] = set()
    while not stop.is_set():
        try:
            if len(running) < concurrency:
                job_id = await _claim()
                if job_id:
                    t = asyncio.create_task(run_job(job_id))
                    running.add(t)
                    t.add_done_callback(running.discard)
                    continue
            await asyncio.wait_for(stop.wait(), timeout=0.5)
        except TimeoutError:
            pass
        except Exception:  # noqa: BLE001
            log.exception("worker loop error")
            await asyncio.sleep(2)
    for t in running:
        t.cancel()
