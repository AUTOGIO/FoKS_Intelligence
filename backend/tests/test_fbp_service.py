from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import fbp_service


@pytest.mark.asyncio
async def test_run_nfa_delegates(monkeypatch):
    dummy_client = MagicMock()
    dummy_client.nfa = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(fbp_service, "_CLIENT", dummy_client)
    result = await fbp_service.run_nfa({"task": "demo"})
    dummy_client.nfa.assert_awaited_with({"task": "demo"})
    assert result == {"ok": True}

