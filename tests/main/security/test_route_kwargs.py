from __future__ import annotations

from inhouse.fastapi.decorator import _route_kwargs


# injected request kwarg is stripped before the route handler runs
def test_strips_request() -> None:
    async def handler(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    kwargs = {"item_id": 1, "request": object()}
    assert "request" not in _route_kwargs(handler, kwargs)
