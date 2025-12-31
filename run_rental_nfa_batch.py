#!/usr/bin/env python3
"""Run NFA creation (real browser form fill) for 2 CPFs via FBP Backend.

This calls FBP's n8n-compatible endpoint `/api/nfa/batch` over the UNIX socket
`/tmp/fbp.sock`, which triggers Playwright automation that fills the SEFAZ-PB ATF
NFA creation form end-to-end (the same flow shown in your screenshots).

Notes:
- Credentials are NOT passed here. FBP will use its own `.env` (`NFA_USERNAME`, `NFA_PASSWORD`).
- Runs in visual mode by default (`headless: false`) for debugging.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import httpx

SOCKET_PATH = "/tmp/fbp.sock"
BASE_URL = "http://localhost"

EMITENTE_CNPJ = "28.842.017/0001-05"
CPFS = [
    "079.478.344-90",
    "460.533.285-53",
]


async def main() -> None:
    screenshots_dir = Path(
        "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/output/nfa/screenshots"
    )
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # NOTE: /api/nfa/batch currently requires explicit `credentials` to perform login.
    # To avoid embedding secrets here, we call /api/nfa/create twice instead.
    # That endpoint falls back to FBP's own env (.env): NFA_USERNAME / NFA_PASSWORD.

    common_config: Dict[str, Any] = {
        "browser": {
            "headless": False,
            "slow_mo": 120,
        },
        "paths": {
            "screenshots_dir": str(screenshots_dir),
        },
        "cdp": {
            "enabled": False,
            "url": "http://localhost:9222",
        },
    }

    def build_create_payload(cpf: str) -> Dict[str, Any]:
        return {
            "emitente": {"cnpj": EMITENTE_CNPJ},
            "destinatario": {"cpf": cpf, "documento": cpf},
            "natureza_operacao": "REMESSA",
            "motivo": "DESPACHO",
            "reparticao_fiscal": "90102008",
            "codigo_municipio": "2051-6",
            "tipo_operacao": "SAIDA",
            "cfop": "6908",
            "produtos": [
                {
                    "ncm": "0000.00.00",
                    "descricao": "1 - SID241",
                    "detalhamento_produto": "1 - SID241",
                    "unidade": "UN",
                    "quantidade": 1,
                    "valor_unitario": 1100,
                    "aliquota": 0,
                    "cst": "41",
                    "receita": "1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)",
                }
            ],
            "informacoes_adicionais": "Remessa por conta de contrato de locacao",
            "config": common_config,
        }

    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(uds=SOCKET_PATH),
        timeout=httpx.Timeout(1800.0),
    ) as client:
        for cpf in CPFS:
            payload = build_create_payload(cpf)
            resp = await client.post(f"{BASE_URL}/api/nfa/create", json=payload)
            resp.raise_for_status()
            results.append({"cpf": cpf, "response": resp.json()})

    out_path = Path("/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/output/nfa")
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / "run_rental_nfa_create_results.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print("/api/nfa/create results written to:")
    print(str(out_file))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
