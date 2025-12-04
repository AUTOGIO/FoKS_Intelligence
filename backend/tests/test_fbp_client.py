from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.fbp_client import FBPClient, FBPClientError


class DummyResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


class DummyClient:
    def __init__(self, response: DummyResponse, *, side_effect=None):
        self.response = response
        self.side_effect = side_effect
        self.request = AsyncMock(side_effect=self._request)

    async def _request(self, *args, **kwargs):
        if self.side_effect:
            raise self.side_effect
        return self.response

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_health_success():
    response = DummyResponse({"status": "ok"})
    client = FBPClient(client_factory=lambda: DummyClient(response))
    result = await client.health()
    assert result["endpoint"] == "/health"
    assert result["payload"]["status"] == "ok"


@pytest.mark.asyncio
async def test_post_routes():
    response = DummyResponse({"ok": True})
    dummy = DummyClient(response)
    client = FBPClient(client_factory=lambda: dummy)
    await client.nfa({"a": 1})
    dummy.request.assert_awaited_with("POST", "/nfa", json={"a": 1})


@pytest.mark.asyncio
async def test_retry_on_timeout():
    timeout = httpx.TimeoutException("boom")
    dummy = DummyClient(DummyResponse({"ok": True}), side_effect=timeout)
    client = FBPClient(client_factory=lambda: dummy)
    with pytest.raises(FBPClientError):
        await client.browser({"x": 1})


@pytest.mark.asyncio
async def test_4xx_error():
    response = DummyResponse({"error": "bad"}, status=400)
    client = FBPClient(client_factory=lambda: DummyClient(response))
    with pytest.raises(FBPClientError):
        await client.redesim({"a": 1})

