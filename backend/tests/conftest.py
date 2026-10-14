"""Tests run against SQLite with mock LLM + mock audio. No network, no paid calls."""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="objection-test-"))
os.environ.update(
    DATABASE_URL=f"sqlite+aiosqlite:///{_TMP / 'test.db'}",
    STORAGE_DIR=str(_TMP / "storage"),
    RUN_WORKER_IN_PROCESS="false",
    REDIS_URL="redis://127.0.0.1:1/0",
    AUDIO_PROVIDER="mock",
    LLM_PROVIDER="mock",
    ENABLE_PAID_TTS="false",
    FISH_AUDIO_API_KEY="",
    ANTHROPIC_API_KEY="",
)

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402,F401
from app.db import Base, configure_engine, engine, session_factory  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
async def _db():
    configure_engine(os.environ["DATABASE_URL"])
    async with engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def session():
    async with session_factory()() as s:
        yield s


@pytest.fixture
async def client():
    from app.main import create_app

    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def run_pending_jobs() -> None:
    """Drain the job queue in-process (the worker is disabled in tests)."""
    import app.services.pipeline  # noqa: F401
    from app.models import AudioGenerationJob
    from app.services.jobs import run_job

    while True:
        async with session_factory()() as s:
            job = (await s.execute(select(AudioGenerationJob).where(AudioGenerationJob.status == "queued")
                                   .order_by(AudioGenerationJob.created_at).limit(1))).scalar_one_or_none()
            if not job:
                return
            job.status = "running"
            await s.commit()
            jid = job.id
        await run_job(jid)


@pytest.fixture
def drain():
    return run_pending_jobs
