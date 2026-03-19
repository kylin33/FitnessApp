from __future__ import annotations

import asyncio
from typing import Awaitable, Callable


async def countdown(
    seconds: int,
    on_tick: Callable[[int], None],
    is_cancelled: Callable[[], bool],
    is_paused: Callable[[], bool],
    tick_seconds: float = 1.0,
) -> bool:
    """Run countdown and return whether it was cancelled."""
    remaining = int(seconds)
    while remaining >= 0:
        if is_cancelled():
            return True
        if is_paused():
            await asyncio.sleep(0.1)
            continue
        on_tick(remaining)
        await asyncio.sleep(tick_seconds)
        remaining -= 1
    return False
