"""Standalone worker: `python -m app.worker`."""

import asyncio
import logging
import signal

from app.services.jobs import worker_loop


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = asyncio.Event()

    async def run() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await worker_loop(stop)

    asyncio.run(run())


if __name__ == "__main__":
    main()
