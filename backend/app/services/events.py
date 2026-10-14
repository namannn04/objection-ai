"""Live event bus for SSE. Redis pub/sub across processes; in-memory fallback
when Redis is unavailable (single-process dev and tests)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import AsyncIterator

from app.config import get_settings

log = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._local: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._redis = None
        self._redis_ok: bool | None = None

    async def _r(self):
        if self._redis_ok is False:
            return None
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=1)
                await self._redis.ping()
                self._redis_ok = True
            except Exception as exc:  # noqa: BLE001
                log.warning("redis unavailable, using in-memory event bus: %s", exc)
                self._redis_ok = False
                self._redis = None
        return self._redis

    async def publish(self, channel: str, event: str, data: dict) -> None:
        msg = json.dumps({"event": event, "data": data}, default=str)
        r = await self._r()
        if r is not None:
            try:
                await r.publish(f"objection:{channel}", msg)
                return
            except Exception as exc:  # noqa: BLE001
                log.warning("redis publish failed: %s", exc)
        for q in list(self._local[channel]):
            q.put_nowait(msg)

    async def subscribe(self, channel: str) -> AsyncIterator[dict]:
        r = await self._r()
        if r is not None:
            pubsub = r.pubsub()
            await pubsub.subscribe(f"objection:{channel}")
            try:
                while True:
                    m = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15)
                    if m is None:
                        yield {"event": "ping", "data": {}}
                        continue
                    yield json.loads(m["data"])
            finally:
                await pubsub.unsubscribe()
                await pubsub.aclose()
        else:
            q: asyncio.Queue = asyncio.Queue()
            self._local[channel].add(q)
            try:
                while True:
                    try:
                        yield json.loads(await asyncio.wait_for(q.get(), timeout=15))
                    except TimeoutError:
                        yield {"event": "ping", "data": {}}
            finally:
                self._local[channel].discard(q)


bus = EventBus()
