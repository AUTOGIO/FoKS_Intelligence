from __future__ import annotations

from typing import Any, Dict

from app.services.fbp_client import FBPClient

_CLIENT = FBPClient()


async def run_health_check() -> Dict[str, Any]:
    return await _CLIENT.health()


async def run_nfa(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await _CLIENT.nfa(payload)


async def run_redesim(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await _CLIENT.redesim(payload)


async def run_browser_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await _CLIENT.browser(payload)


async def run_utils(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await _CLIENT.utils(payload)

