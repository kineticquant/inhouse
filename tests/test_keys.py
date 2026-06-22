from __future__ import annotations

from inhouse.keys import make_cache_key


def sample_func(x: int, label: str = "a") -> str:
    return f"{x}-{label}"


def test_same_arguments_produce_same_key() -> None:
    key_a = make_cache_key(sample_func, (1,), {"label": "a"})
    key_b = make_cache_key(sample_func, (1,), {"label": "a"})
    assert key_a == key_b


def test_different_arguments_produce_different_keys() -> None:
    key_a = make_cache_key(sample_func, (1,), {"label": "a"})
    key_b = make_cache_key(sample_func, (2,), {"label": "a"})
    assert key_a != key_b


def test_keyword_argument_order_is_irrelevant() -> None:
    key_a = make_cache_key(sample_func, (), {"a": 1, "b": 2})
    key_b = make_cache_key(sample_func, (), {"b": 2, "a": 1})
    assert key_a == key_b


def test_nested_mapping_key_order_is_irrelevant() -> None:
    key_a = make_cache_key(sample_func, (), {"payload": {"a": 1, "b": 2}})
    key_b = make_cache_key(sample_func, (), {"payload": {"b": 2, "a": 1}})
    assert key_a == key_b


def test_excluded_types_are_ignored() -> None:
    class DummyRequest:
        pass

    key_a = make_cache_key(
        sample_func,
        (DummyRequest(), 1),
        {"label": "a"},
        exclude_types=(DummyRequest,),
    )
    key_b = make_cache_key(sample_func, (1,), {"label": "a"}, exclude_types=(DummyRequest,))
    assert key_a == key_b


def test_excluded_type_subclasses_are_ignored() -> None:
    class DummyRequest:
        pass

    class SubRequest(DummyRequest):
        pass

    key_a = make_cache_key(
        sample_func,
        (SubRequest(), 1),
        {"label": "a"},
        exclude_types=(DummyRequest,),
    )
    key_b = make_cache_key(sample_func, (1,), {"label": "a"}, exclude_types=(DummyRequest,))
    assert key_a == key_b


def test_key_contains_function_identity() -> None:
    key = make_cache_key(sample_func, (1,), {})
    assert key.startswith(f"{sample_func.__module__}.{sample_func.__qualname__}:")
