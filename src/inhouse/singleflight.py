from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from typing import Any, TypeVar

T = TypeVar("T")


def _release_async_waiters(future: asyncio.Future[Any], exc: BaseException) -> None:
    if future.done():
        return
    if isinstance(exc, asyncio.CancelledError):
        future.cancel()
    else:
        future.set_exception(exc)


def _release_sync_waiters(future: Future[Any], exc: BaseException) -> None:
    if not future.done():
        future.set_exception(exc)


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

        async def run() -> T:
            try:
                result = await compute()
            except BaseException as exc:
                _release_async_waiters(future, exc)
                raise
            else:
                if not future.done():
                    future.set_result(result)
                return result
            finally:
                async with self._guard:
                    self._inflight.pop(key, None)

        try:
            return await asyncio.shield(run())
        except asyncio.CancelledError:
            raise


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
        except BaseException as exc:
            _release_sync_waiters(future, exc)
            raise
        else:
            future.set_result(result)
            return result
        finally:
            with self._guard:
                self._inflight.pop(key, None)
