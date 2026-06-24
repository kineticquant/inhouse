from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from inhouse.keys import make_weak_etag


@dataclass(frozen=True, slots=True)
class HttpCacheOutcome:
    status_code: int
    headers: dict[str, str]
    body: Any | None


# ponytail: exact if-none-match match only; no weak/strong normalization beyond strip
def etag_matches(if_none_match: str | None, etag: str | None) -> bool:
    return bool(if_none_match and etag and any(part.strip() == etag for part in if_none_match.split(",")))  # noqa: E501


def etag_for_value(value: Any, *, enabled: bool) -> str | None:
    return make_weak_etag(value) if enabled else None


def cache_control_header(remaining_ttl: float, *, visibility: Literal["private", "public"] = "private") -> str:  # noqa: E501
    return f"{visibility}, max-age={max(0, int(math.ceil(remaining_ttl)))}"


def http_cache_headers(*, remaining_ttl: float | None, http_cache: bool, cache_visibility: Literal["private", "public"], etag: str | None) -> dict[str, str]:  # noqa: E501
    headers: dict[str, str] = {}
    if http_cache and remaining_ttl is not None:
        headers["Cache-Control"] = cache_control_header(remaining_ttl, visibility=cache_visibility)
    if etag is not None:
        headers["ETag"] = etag
    return headers


def http_cache_outcome(body: Any, *, if_none_match: str | None, remaining_ttl: float | None, stored_etag: str | None, http_cache: bool, cache_visibility: Literal["private", "public"], use_etag: bool) -> HttpCacheOutcome:  # noqa: E501
    def headers(etag: str | None) -> dict[str, str]:
        return http_cache_headers(
            remaining_ttl=remaining_ttl,
            http_cache=http_cache,
            cache_visibility=cache_visibility,
            etag=etag,
        )

    if use_etag and etag_matches(if_none_match, stored_etag):
        return HttpCacheOutcome(304, headers(stored_etag), None)
    return HttpCacheOutcome(200, headers(stored_etag if use_etag else None), body)
