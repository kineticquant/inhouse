from __future__ import annotations

from inhouse import MemoryStore, cache, etag_matches, http_cache_outcome, make_weak_etag
from inhouse.http_cache import cache_control_header, http_cache_headers
from inhouse.keys import make_cache_key


def test_etag_matches_exact_and_list() -> None:
    tag = 'W/"abc"'
    assert etag_matches(f'  {tag}  , W/"other"', tag)
    assert not etag_matches('W/"other"', tag)
    assert not etag_matches(None, tag)
    assert not etag_matches(tag, None)


def test_cache_control_header_ceils_remaining_ttl() -> None:
    assert cache_control_header(30.1) == "private, max-age=31"
    assert cache_control_header(0.0, visibility="public") == "public, max-age=0"


def test_http_cache_outcome_304_vs_200() -> None:
    tag = 'W/"abc"'
    body = {"id": 1}
    not_modified = http_cache_outcome(
        body,
        if_none_match=tag,
        remaining_ttl=30.0,
        stored_etag=tag,
        http_cache=True,
        cache_visibility="private",
        use_etag=True,
    )
    assert not_modified.status_code == 304
    assert not_modified.body is None
    assert not_modified.headers["ETag"] == tag
    assert not_modified.headers["Cache-Control"] == "private, max-age=30"

    full = http_cache_outcome(
        body,
        if_none_match='W/"stale"',
        remaining_ttl=30.0,
        stored_etag=tag,
        http_cache=False,
        cache_visibility="private",
        use_etag=True,
    )
    assert full.status_code == 200
    assert full.body == body
    assert full.headers == {"ETag": tag}


def test_http_cache_headers_omits_disabled_parts() -> None:
    assert http_cache_headers(
        remaining_ttl=10.0,
        http_cache=False,
        cache_visibility="private",
        etag='W/"x"',
    ) == {"ETag": 'W/"x"'}
    assert http_cache_headers(
        remaining_ttl=None,
        http_cache=True,
        cache_visibility="public",
        etag=None,
    ) == {}


def test_inhouse_cache_stores_weak_etag() -> None:
    store = MemoryStore()
    body = {"n": 1}
    expected = make_weak_etag(body)

    @cache(60, store=store, etag=True)
    def load() -> dict[str, int]:
        return body

    assert load() == body
    key = make_cache_key(load, (), {})
    assert store.get_etag(key) == expected
