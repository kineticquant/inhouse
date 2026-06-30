from __future__ import annotations

import dataclasses

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


def test_different_types_with_same_str_produce_different_keys() -> None:
    class Alpha:
        def __str__(self) -> str:
            return "same"

    class Beta:
        def __str__(self) -> str:
            return "same"

    key_a = make_cache_key(sample_func, (Alpha(),), {})
    key_b = make_cache_key(sample_func, (Beta(),), {})
    assert key_a != key_b


def test_same_type_and_str_produce_same_key() -> None:
    class Widget:
        def __init__(self, label: str) -> None:
            self.label = label

        def __str__(self) -> str:
            return self.label

    key_a = make_cache_key(sample_func, (Widget("x"),), {})
    key_b = make_cache_key(sample_func, (Widget("x"),), {})
    assert key_a == key_b


def test_set_argument_order_is_irrelevant() -> None:
    key_a = make_cache_key(sample_func, ({1, 2, 3},), {})
    key_b = make_cache_key(sample_func, ({3, 2, 1},), {})
    assert key_a == key_b


def test_list_and_tuple_produce_different_keys() -> None:
    key_a = make_cache_key(sample_func, ([1, 2],), {})
    key_b = make_cache_key(sample_func, ((1, 2),), {})
    assert key_a != key_b


@dataclasses.dataclass
class SampleRecord:
    user_id: int
    label: str


def test_dataclass_arguments_are_stable() -> None:
    key_a = make_cache_key(sample_func, (SampleRecord(1, "a"),), {})
    key_b = make_cache_key(sample_func, (SampleRecord(1, "a"),), {})
    assert key_a == key_b


class PydanticLike:
    model_fields = {"name": object(), "count": object()}

    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count

    def model_dump(self) -> dict[str, object]:
        return {"name": self.name, "count": self.count}


def test_pydantic_like_arguments_are_stable() -> None:
    key_a = make_cache_key(sample_func, (PydanticLike("x", 1),), {})
    key_b = make_cache_key(sample_func, (PydanticLike("x", 1),), {})
    assert key_a == key_b


def test_nested_mapping_freezing_is_stable() -> None:
    key_a = make_cache_key(sample_func, (), {"filters": {"tags": {"a", "b"}, "ids": [1, 2]}})
    key_b = make_cache_key(sample_func, (), {"filters": {"ids": [1, 2], "tags": {"b", "a"}}})
    assert key_a == key_b
