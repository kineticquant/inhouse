from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncSingleflight:
    """Coalesce concurrent async computations for the same cache key."""

    def __init__(self) -> None:
        self._inflight: dict[str, asyncio.Future[Any]] = {}
        self._guard = asyncio.Lock()

    async def do(self, key: str, compute: Callable[[], Awaitable[T]]) -> T:
        async with self._guard:
            future = self._inflight.get(key)
            if future is None:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self._inflight[key] = future
                leader = True
            else:
                leader = False

        if not leader:
            result: T = await future
            return result

        try:
            result = await compute()
        except Exception as exc:
            if not future.done():
                future.set_exception(exc)
            raise
        else:
            if not future.done():
                future.set_result(result)
            return result
        finally:
            async with self._guard:
                self._inflight.pop(key, None)


class SyncSingleflight:
    """Coalesce concurrent sync computations for the same cache key."""

    def __init__(self) -> None:
        self._inflight: dict[str, Future[Any]] = {}
        self._guard = threading.Lock()

    def do(self, key: str, compute: Callable[[], T]) -> T:
        with self._guard:
            future = self._inflight.get(key)
            if future is None:
                future = Future()
                self._inflight[key] = future
                leader = True
            else:
                leader = False

        if not leader:
            result: T = future.result()
            return result

        try:
            result = compute()
        except Exception as exc:
            future.set_exception(exc)
            raise
        else:
            future.set_result(result)
            return result
        finally:
            with self._guard:
                self._inflight.pop(key, None)
