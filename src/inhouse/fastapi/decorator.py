from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal, cast

from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from inhouse.decorator import _resolve_ttl, get_default_store, inhouse_cache
from inhouse.fastapi.keys import make_fastapi_cache_key
from inhouse.http_cache import HttpCacheOutcome, etag_for_value, http_cache_outcome
from inhouse.singleflight import AsyncSingleflight, SyncSingleflight
from inhouse.store import MISS, MemoryStore

TtlSource = float | Callable[[], float] | None

_ASYNC_SINGLEFLIGHT = AsyncSingleflight()
_SYNC_SINGLEFLIGHT = SyncSingleflight()


# add request: Request to wrapper signature so fastapi injects it for if-none-match reads
def _ensure_request_in_signature(wrapper: Callable[..., Any], func: Callable[..., Any]) -> None:
    sig = inspect.signature(func)
    if any(p.name == "request" for p in sig.parameters.values()):
        return
    # ponytail: **kwargs routes must declare request: Request for if-none-match reads
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return
    cast(Any, wrapper).__signature__ = inspect.Signature(parameters=[*sig.parameters.values(), inspect.Parameter("request", inspect.Parameter.KEYWORD_ONLY, annotation=Request)])  # noqa: E501


def _route_kwargs(func: Callable[..., Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return kwargs if any(p.name == "request" for p in inspect.signature(func).parameters.values()) else {k: v for k, v in kwargs.items() if k != "request"}  # noqa: E501


def _http_response(outcome: HttpCacheOutcome) -> Response:
    return Response(status_code=304, headers=outcome.headers) if outcome.status_code == 304 else JSONResponse(content=jsonable_encoder(outcome.body), headers=outcome.headers, status_code=200)  # noqa: E501


def _respond(body: Any, *, cache_key: str, target_store: MemoryStore, if_none_match: str | None, http_cache: bool, cache_visibility: Literal["private", "public"], use_etag: bool) -> Response:  # noqa: E501
    remaining, stored_etag = target_store.entry_meta(cache_key) or (None, None)
    return _http_response(http_cache_outcome(body, if_none_match=if_none_match, remaining_ttl=remaining, stored_etag=stored_etag, http_cache=http_cache, cache_visibility=cache_visibility, use_etag=use_etag))  # noqa: E501


def _cache_set(target_store: MemoryStore, cache_key: str, result: Any, ttl_seconds: TtlSource, *, sliding: bool, etag: bool) -> None:  # noqa: E501
    target_store.set(cache_key, result, _resolve_ttl(target_store, ttl_seconds), sliding=sliding, etag=etag_for_value(result, enabled=etag))  # noqa: E501


def _http_cache(func: Callable[..., Any], *, async_: bool, ttl_seconds: TtlSource, store: MemoryStore | None, key_builder: Callable[..., str], sliding: bool, http_cache: bool, cache_visibility: Literal["private", "public"], etag: bool) -> Callable[..., Any]:  # noqa: E501
    singleflight = _ASYNC_SINGLEFLIGHT if async_ else _SYNC_SINGLEFLIGHT

    def ctx(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[MemoryStore, str, Callable[[Any], Response]]:  # noqa: E501
        target_store = store or get_default_store()
        cache_key = key_builder(func, args, kwargs, exclude_types=())
        request = kwargs.get("request")
        if_none_match = request.headers.get("if-none-match") if request else None

        def respond(body: Any) -> Response:
            return _respond(body, cache_key=cache_key, target_store=target_store, if_none_match=if_none_match, http_cache=http_cache, cache_visibility=cache_visibility, use_etag=etag)  # noqa: E501

        return target_store, cache_key, respond

    if async_:

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            target_store, cache_key, respond = ctx(args, kwargs)
            if (cached := target_store.get(cache_key)) is not MISS:
                return respond(cached)

            async def compute() -> Any:
                if (recheck := target_store.get(cache_key)) is not MISS:
                    return recheck
                result = await func(*args, **_route_kwargs(func, kwargs))
                _cache_set(target_store, cache_key, result, ttl_seconds, sliding=sliding, etag=etag)
                return result

            return respond(await singleflight.do(cache_key, compute))
    else:

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            target_store, cache_key, respond = ctx(args, kwargs)
            if (cached := target_store.get(cache_key)) is not MISS:
                return respond(cached)

            def compute() -> Any:
                if (recheck := target_store.get(cache_key)) is not MISS:
                    return recheck
                result = func(*args, **_route_kwargs(func, kwargs))
                _cache_set(target_store, cache_key, result, ttl_seconds, sliding=sliding, etag=etag)
                return result

            return respond(singleflight.do(cache_key, compute))

    _ensure_request_in_signature(wrapper, func)
    return wrapper


def fastapi_cache(ttl_seconds: TtlSource = None, *, store: MemoryStore | None = None, key_builder: Callable[..., str] | None = None, sliding: bool = False, http_cache: bool = False, cache_visibility: Literal["private", "public"] = "private", etag: bool = False) -> Callable[[Any], Any]:  # noqa: E501
    if not http_cache and not etag:
        return inhouse_cache(ttl_seconds, store=store, key_builder=key_builder or make_fastapi_cache_key, sliding=sliding)  # noqa: E501
    kb = key_builder or make_fastapi_cache_key
    return lambda func: _http_cache(func, async_=inspect.iscoroutinefunction(func), ttl_seconds=ttl_seconds, store=store, key_builder=kb, sliding=sliding, http_cache=http_cache, cache_visibility=cache_visibility, etag=etag)  # noqa: E501
