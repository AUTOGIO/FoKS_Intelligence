#!/usr/bin/env python3
"""
Execute NFA trigger workflow for multiple CPFs.

This script sends POST requests to /tasks/nfa endpoint for each CPF provided.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List

import httpx


async def trigger_nfa(cpf: str, loja: str, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Trigger NFA automation for a given CPF.

    Args:
        cpf: CPF number (formatted or unformatted)
        loja: Store/loja identifier (for logging)
        base_url: Base URL of FoKS server

    Returns:
        Dictionary with response data
    """
    url = f"{base_url}/tasks/nfa"
    payload = {
        "cpf": cpf,
        "test": False,  # Set to True for testing
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            return {
                "loja": loja,
                "cpf": cpf,
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "status_code": response.status_code,
                "fbp_response": result.get("fbp_response", {}),
            }
    except httpx.HTTPStatusError as e:
        return {
            "loja": loja,
            "cpf": cpf,
            "success": False,
            "message": f"HTTP {e.response.status_code}: {e.response.text}",
            "status_code": e.response.status_code,
            "error": str(e),
        }
    except httpx.RequestError as e:
        return {
            "loja": loja,
            "cpf": cpf,
            "success": False,
            "message": f"Request failed: {str(e)}",
            "status_code": 0,
            "error": str(e),
        }
    except Exception as e:
        return {
            "loja": loja,
            "cpf": cpf,
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "status_code": 0,
            "error": str(e),
        }


async def execute_batch(items: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Execute NFA trigger for multiple CPFs.

    Args:
        items: List of dictionaries with 'loja' and 'cpf' keys

    Returns:
        List of results for each CPF
    """
    print(f"Executing NFA trigger for {len(items)} CPFs...\n")

    tasks = [trigger_nfa(item["cpf"], item["loja"]) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(
                {
                    "loja": items[i]["loja"],
                    "cpf": items[i]["cpf"],
                    "success": False,
                    "message": f"Exception: {str(result)}",
                    "status_code": 0,
                    "error": str(result),
                }
            )
        else:
            processed_results.append(result)

    return processed_results


async def main() -> None:
    """Main entry point."""
    # Data provided by user
    items = [
        {
            "loja": "SP228- Remessa por conta de contrato de locação",
            "cpf": "228.240.248-01",
        },
        {
            "loja": "SP233- Remessa por conta de contrato de locação",
            "cpf": "113.684.248.99",  # Note: This might need to be "113.684.248-99"
        },
        {
            "loja": "SP242- Remessa por conta de contrato de locação",
            "cpf": "512.810.178-92",
        },
    ]

    # Fix potential formatting issue in second CPF
    if items[1]["cpf"] == "113.684.248.99":
        print("⚠️  Warning: CPF format might be incorrect (113.684.248.99)")
        print("   Expected format: 113.684.248-99")
        print("   Proceeding with provided value...\n")

    results = await execute_batch(items)

    # Print results
    print("\n" + "=" * 80)
    print("NFA TRIGGER RESULTS")
    print("=" * 80 + "\n")

    for result in results:
        status_icon = "✅" if result["success"] else "❌"
        print(f"{status_icon} {result['loja']}")
        print(f"   CPF: {result['cpf']}")
        print(f"   Status: {result['message']}")
        if result.get("status_code"):
            print(f"   HTTP Status: {result['status_code']}")
        if result.get("error"):
            print(f"   Error: {result['error']}")
        print()

    # Summary
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful

    print("=" * 80)
    print(f"SUMMARY: {successful} successful, {failed} failed")
    print("=" * 80)

    # Output JSON for programmatic use
    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
