"""The lock a conversation's turns take, which also reports when a turn
starts and ends -- the desktop app saves a download from the
conversation's browser tab without asking only while one is under way."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable
from typing import Literal


class TurnLock(asyncio.Lock):
    def __init__(self, on_change: Callable[[bool], None]) -> None:
        super().__init__()
        self._on_change = on_change
        # When the turn holding the lock took it, in ms since the epoch.
        self.turn_started_at: float | None = None

    async def acquire(self) -> Literal[True]:
        await super().acquire()
        self.turn_started_at = time.time() * 1000
        self._on_change(True)
        return True

    def release(self) -> None:
        self.turn_started_at = None
        super().release()
        self._on_change(False)

    async def wait_released(self, timeout: float) -> None:
        """Returns once no turn holds the lock, or after `timeout` seconds."""
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self.acquire(), timeout)
            self.release()
