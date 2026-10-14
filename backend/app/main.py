from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import cases, sessions, system
from app.config import get_settings
from app.services.audio_generation import FIXTURE_DIR, ensure_sfx_fixtures

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    ensure_sfx_fixtures()
    stop = asyncio.Event()
    task = None
    if cfg.run_worker_in_process:
        from app.services.jobs import worker_loop

        task = asyncio.create_task(worker_loop(stop))
    yield
    stop.set()
    if task:
        await asyncio.wait([task], timeout=5)


def create_app() -> FastAPI:
    cfg = get_settings()
    app = FastAPI(
        title="Objection AI — The Court of Absolute Nonsense",
        version="0.1.0",
        description="Multi-agent comedy courtroom with Fish Audio Drama 3 performances.",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in cfg.cors_origins.split(",")],
                       allow_methods=["*"], allow_headers=["*"])
    app.include_router(cases.router)
    app.include_router(sessions.router)
    app.include_router(system.router)
    app.mount("/media/audio", StaticFiles(directory=cfg.audio_dir), name="audio")
    app.mount("/media/exports", StaticFiles(directory=cfg.export_dir), name="exports")
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/media/sfx", StaticFiles(directory=FIXTURE_DIR), name="sfx")
    return app


app = create_app()
