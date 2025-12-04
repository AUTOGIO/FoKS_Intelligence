#!/usr/bin/env python3
"""
LM Studio health checker.

Confirms:
- /v1/models reachable
- At least one model present
- Streaming endpoint responds with a small chunk
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional


try:
    import httpx
except ImportError as exc:  # pragma: no cover - simple dependency guard
    print("ERROR: httpx is not installed. Activate the FoKS or LM Studio venv and run: pip install httpx", file=sys.stderr)
    raise SystemExit(1) from exc


BASE_URL = "http://127.0.0.1:1234"
MODELS_ENDPOINT = "/v1/models"
CHAT_ENDPOINT = "/v1/chat/completions"


def get_models(client: httpx.Client) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}{MODELS_ENDPOINT}"
    response = client.get(url, timeout=3.0)
    response.raise_for_status()
    data = response.json()
    models = data.get("data") or data.get("models") or []
    if not isinstance(models, list):
        raise ValueError("Unexpected models payload from LM Studio")
    return models  # type: ignore[return-value]


def pick_default_model(models: List[Dict[str, Any]]) -> Optional[str]:
    for model in models:
        if model.get("id"):
            return str(model["id"])
    if models:
        model = models[0]
        if model.get("id"):
            return str(model["id"])
    return None


def check_streaming(client: httpx.Client, model: str) -> bool:
    url = f"{BASE_URL}{CHAT_ENDPOINT}"
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "stream": True,
        "max_tokens": 8,
    }
    with client.stream("POST", url, json=payload, timeout=10.0) as response:
        response.raise_for_status()
        for chunk in response.iter_text():
            if chunk.strip():
                print(f"[OK] Streaming chunk received from model '{model}': {chunk[:80]!r}")
                return True
    return False


def main() -> int:
    print("LM Studio health check starting...")
    try:
        with httpx.Client() as client:
            models = get_models(client)
            if not models:
                print("[FAIL] No models reported by LM Studio", file=sys.stderr)
                return 1

            print(f"[OK] /v1/models reachable; {len(models)} model(s) reported")
            print(json.dumps(models[:3], indent=2, ensure_ascii=False))

            default_model = pick_default_model(models)
            if not default_model:
                print("[FAIL] Could not determine a default model id from LM Studio payload", file=sys.stderr)
                return 1

            print(f"Using model '{default_model}' for streaming test")
            if not check_streaming(client, default_model):
                print("[FAIL] Streaming endpoint did not return any chunks", file=sys.stderr)
                return 1
    except httpx.HTTPError as exc:
        print(f"[FAIL] LM Studio HTTP error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - safety net
        print(f"[FAIL] LM Studio health unexpected error: {exc}", file=sys.stderr)
        return 1

    print("LM Studio health check: ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


