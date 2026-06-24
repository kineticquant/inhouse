from __future__ import annotations

import inspect
import math
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal

from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from inhouse.decorator import _resolve_ttl, get_default_store, inhouse_cache
from inhouse.fastapi.keys import make_fastapi_cache_key
from inhouse.keys import make_weak_etag
from inhouse.singleflight import AsyncSingleflight, SyncSingleflight
from inhouse.store import MISS, MemoryStore

TtlSource = float | Callable[[], float] | None

_ASYNC_SINGLEFLIGHT = AsyncSingleflight()
_SYNC_SINGLEFLIGHT = SyncSingleflight()


# add request: Request to wrapper signature so fastapi injects it for if-none-match reads
def _ensure_request_in_signature(wrapper: Callable[..., Any], func: Callable[..., Any]) -> None:
    sig = inspect.signature(func)
    if any(param.name == "request" for param in sig.parameters.values()):
        return
    # ponytail: **kwargs routes must declare request: Request for if-none-match reads
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values()):
        return
    params = [
        *sig.parameters.values(),
        inspect.Parameter("request", inspect.Parameter.KEYWORD_ONLY, annotation=Request),
    ]
    wrapper.__signature__ = inspect.Signature(parameters=params)


# drop injected request kwarg before calling the route handler (unless handler declared it)
def _route_kwargs(func: Callable[..., Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    if any(param.name == "request" for param in inspect.signature(func).parameters.values()):
        return kwargs
    return {key: value for key, value in kwargs.items() if key != "request"}


# ponytail: exact if-none-match match only; no weak/strong normalization beyond strip
def _etag_matches(if_none_match: str | None, etag: str | None) -> bool:
    if not if_none_match or not etag:
        return False
    return any(part.strip() == etag for part in if_none_match.split(","))


# build cache-control and/or etag response headers; 304 when status_code says so
def _http_response(body: Any, *, status_code: int, http_cache: bool, cache_visibility: Literal["private", "public"], remaining_ttl: float | None, etag: str | None) -> Response:  # noqa: E501
    headers: dict[str, str] = {}
    if http_cache and remaining_ttl is not None:
        max_age = max(0, int(math.ceil(remaining_ttl)))
        headers["Cache-Control"] = f"{cache_visibility}, max-age={max_age}"
    if etag is not None:
        headers["ETag"] = etag
    if status_code == 304:
        return Response(status_code=304, headers=headers)
    return JSONResponse(content=jsonable_encoder(body), headers=headers, status_code=status_code)


# serve cached body as http response, or 304 when if-none-match matches stored etag
def _respond(body: Any, *, cache_key: str, target_store: MemoryStore, if_none_match: str | None, http_cache: bool, cache_visibility: Literal["private", "public"], use_etag: bool) -> Response:  # noqa: E501
    meta = target_store.entry_meta(cache_key)
    remaining, stored_etag = meta if meta is not None else (None, None)
    common = {"http_cache": http_cache, "cache_visibility": cache_visibility, "remaining_ttl": remaining}  # noqa: E501
    if use_etag and _etag_matches(if_none_match, stored_etag):
        return _http_response(None, status_code=304, etag=stored_etag, **common)
    return _http_response(body, status_code=200, etag=stored_etag if use_etag else None, **common)


# write-through to memory store with resolved ttl, sliding flag, and optional etag
def _cache_set(target_store: MemoryStore, cache_key: str, result: Any, ttl_seconds: TtlSource, *, sliding: bool, etag: bool) -> None:  # noqa: E501
    ttl = _resolve_ttl(target_store, ttl_seconds)
    tag = make_weak_etag(result) if etag else None
    target_store.set(cache_key, result, ttl, sliding=sliding, etag=tag)


# async fastapi route wrapper with http cache-control and/or etag/304 support
def _async_http_cache(func: Callable[..., Any], *, ttl_seconds: TtlSource, store: MemoryStore | None, key_builder: Callable[..., str], sliding: bool, http_cache: bool, cache_visibility: Literal["private", "public"], etag: bool) -> Callable[..., Any]:  # noqa: E501
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        target_store = store or get_default_store()
        cache_key = key_builder(func, args, kwargs, exclude_types=())
        request = kwargs.get("request")
        if_none_match = request.headers.get("if-none-match") if request else None
        respond = lambda body: _respond(body, cache_key=cache_key, target_store=target_store, if_none_match=if_none_match, http_cache=http_cache, cache_visibility=cache_visibility, use_etag=etag)  # noqa: E731, E501

        cached = target_store.get(cache_key)
        if cached is not MISS:
            return respond(cached)

        async def compute() -> Any:
            recheck = target_store.get(cache_key)
            if recheck is not MISS:
                return recheck
            result = await func(*args, **_route_kwargs(func, kwargs))
            _cache_set(target_store, cache_key, result, ttl_seconds, sliding=sliding, etag=etag)
            return result

        return respond(await _ASYNC_SINGLEFLIGHT.do(cache_key, compute))

    _ensure_request_in_signature(async_wrapper, func)
    return async_wrapper


# sync fastapi route wrapper with http cache-control and/or etag/304 support
def _sync_http_cache(func: Callable[..., Any], *, ttl_seconds: TtlSource, store: MemoryStore | None, key_builder: Callable[..., str], sliding: bool, http_cache: bool, cache_visibility: Literal["private", "public"], etag: bool) -> Callable[..., Any]:  # noqa: E501
    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        target_store = store or get_default_store()
        cache_key = key_builder(func, args, kwargs, exclude_types=())
        request = kwargs.get("request")
        if_none_match = request.headers.get("if-none-match") if request else None
        respond = lambda body: _respond(body, cache_key=cache_key, target_store=target_store, if_none_match=if_none_match, http_cache=http_cache, cache_visibility=cache_visibility, use_etag=etag)  # noqa: E731, E501

        cached = target_store.get(cache_key)
        if cached is not MISS:
            return respond(cached)

        def compute() -> Any:
            recheck = target_store.get(cache_key)
            if recheck is not MISS:
                return recheck
            result = func(*args, **_route_kwargs(func, kwargs))
            _cache_set(target_store, cache_key, result, ttl_seconds, sliding=sliding, etag=etag)
            return result

        return respond(_SYNC_SINGLEFLIGHT.do(cache_key, compute))

    _ensure_request_in_signature(sync_wrapper, func)
    return sync_wrapper


# cache decorator excluding starlette request/response from keys; optional http caching
def fastapi_cache(ttl_seconds: TtlSource = None, *, store: MemoryStore | None = None, key_builder: Callable[..., str] | None = None, sliding: bool = False, http_cache: bool = False, cache_visibility: Literal["private", "public"] = "private", etag: bool = False) -> Callable[[Any], Any]:  # noqa: E501
    if not http_cache and not etag:
        return inhouse_cache(ttl_seconds, store=store, key_builder=key_builder or make_fastapi_cache_key, sliding=sliding)  # noqa: E501

    resolved_key_builder = key_builder or make_fastapi_cache_key
    http_opts = {
        "ttl_seconds": ttl_seconds,
        "store": store,
        "key_builder": resolved_key_builder,
        "sliding": sliding,
        "http_cache": http_cache,
        "cache_visibility": cache_visibility,
        "etag": etag,
    }

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            return _async_http_cache(func, **http_opts)
        return _sync_http_cache(func, **http_opts)

    return decorator
