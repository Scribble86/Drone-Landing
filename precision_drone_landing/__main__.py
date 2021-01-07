"""The entry point of the program. This file contains the main loop."""

import asyncio
from typing import Callable, Awaitable

from config import SECONDS_PER_FRAME
from target_finder import TargetFinder


async def main_loop(body: Callable[[], Awaitable]):
    """The main loop of the program.

    This loop starts each frame and waits the appropriate amount of time for
    the next frame to start. Each frame, it calls the body() coroutine."""
    loop = asyncio.get_running_loop()
    now = loop.time()
    last_frame = now
    next_frame = now + SECONDS_PER_FRAME

    while True:
        now = loop.time()
        if now >= next_frame:
            print(f'Instantaneous FPS: {1/(now-last_frame):5.1f}')
            last_frame = now
            next_frame = now + SECONDS_PER_FRAME
            await body()
        else:
            await asyncio.sleep(next_frame - loop.time())

if __name__ == '__main__':
    targeting = TargetFinder()
    asyncio.run(main_loop(targeting.loop_body))
