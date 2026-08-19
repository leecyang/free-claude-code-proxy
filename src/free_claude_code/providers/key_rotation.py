"""Round-robin credential rotation for providers with multiple upstream API keys."""

import asyncio
from collections.abc import Sequence


class KeyRotator:
    """Cycle through configured API keys, advancing on every credential fetch.

    The OpenAI SDK re-invokes an async credential provider on every request
    (including retries), so simply advancing the index on each call gives
    both round-robin distribution and next-key failover on retry.
    """

    def __init__(self, keys: Sequence[str]) -> None:
        if not keys:
            raise ValueError("KeyRotator requires at least one key")
        self._keys = tuple(keys)
        self._index = 0
        self._lock = asyncio.Lock()

    async def next_key(self) -> str:
        """Return the next key in rotation order."""
        async with self._lock:
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key
