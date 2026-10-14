"""InterventionService: live chaos-mode interventions (implemented in Phase 5)."""

from __future__ import annotations

from app.services.session_service import SessionError


async def submit_free_text(s, sess, case, scene_key: str, text: str) -> dict:
    raise SessionError("Free-text interventions are not available yet.", 501)
