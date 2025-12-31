#!/usr/bin/env python3
"""Batch process CPF entries from data_input_final through FoKS NFA."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx

# FoKS API endpoint
FOKS_BASE_URL = "http://localhost:8000"
FOKS_NFA_ENDPOINT = f"{FOKS_BASE_URL}/tasks/nfa"


def clean_cpf(cpf: str) -> str:
    """
    Remove formatting from CPF (dots and dashes).

    Args:
        cpf: CPF string (formatted or unformatted)

    Returns:
        Clean CPF with only digits
    """
    return re.sub(r"[.\-]", "", cpf.strip())


async def process_cpf(
    client: httpx.AsyncClient,
    cpf: str,
    loja: str,
    test_mode: bool,
    delay: float,
) -> Dict[str, Any]:
    """
    Process a single CPF through FoKS NFA endpoint.

    Args:
        client: HTTP client instance
        cpf: CPF to process (will be cleaned)
        loja: Store/loja identifier for logging
        test_mode: Whether to run in test mode
        delay: Delay after request (seconds)

    Returns:
        Dictionary with processing result
    """
    cpf_clean = clean_cpf(cpf)
    result = {
        "cpf": cpf_clean,
        "cpf_formatted": cpf,
        "loja": loja,
        "success": False,
        "message": "",
        "error": None,
        "fbp_response": None,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        payload = {"cpf": cpf_clean, "test": test_mode}
        # 2 minute timeout for NFA processing
        response = await client.post(
            FOKS_NFA_ENDPOINT,
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        result["success"] = data.get("success", False)
        result["message"] = data.get("message", "")
        result["fbp_response"] = data.get("fbp_response", {})

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        result["error"] = f"HTTP {status_code}: {exc.response.text}"
        result["message"] = f"Request failed: {status_code}"
        try:
            error_data = exc.response.json()
            result["message"] = error_data.get("detail", result["message"])
        except Exception:
            pass

    except httpx.TimeoutException:
        result["error"] = "Request timeout (120s)"
        result["message"] = "NFA processing timed out"

    except httpx.RequestError as exc:
        result["error"] = f"Connection error: {str(exc)}"
        result["message"] = "Failed to connect to FoKS backend"

    except Exception as exc:  # noqa: BLE001
        result["error"] = f"Unexpected error: {str(exc)}"
        result["message"] = f"Unexpected error: {type(exc).__name__}"

    # Add delay between requests
    if delay > 0:
        await asyncio.sleep(delay)

    return result


async def process_batch(
    input_file: Path,
    test_mode: bool,
    delay: float,
    output_file: Path | None,
) -> None:
    """
    Process batch of CPFs from JSON file.

    Args:
        input_file: Path to JSON input file
        test_mode: Whether to run in test mode
        delay: Delay between requests (seconds)
        output_file: Optional path to write results JSON
    """
    # Read input file
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"❌ Error: Invalid JSON in {input_file}: {exc}")
        sys.exit(1)

    if not isinstance(data, list):
        print(f"❌ Error: Expected JSON array, got {type(data).__name__}")
        sys.exit(1)

    total = len(data)
    print(f"📋 Found {total} entries in {input_file}")
    print(f"⚙️  Test mode: {test_mode}")
    print(f"⏱️  Delay between requests: {delay}s")
    print(f"🌐 FoKS endpoint: {FOKS_NFA_ENDPOINT}")
    print()

    # Process entries
    results: List[Dict[str, Any]] = []
    success_count = 0
    failure_count = 0

    async with httpx.AsyncClient(timeout=120.0) as client:
        for idx, entry in enumerate(data, 1):
            cpf = entry.get("cpf", "")
            loja = entry.get("loja", "Unknown")

            if not cpf:
                print(
                    f"⚠️  [{idx}/{total}] Skipping entry {idx}: No CPF found"
                )
                results.append(
                    {
                        "cpf": "",
                        "loja": loja,
                        "success": False,
                        "message": "No CPF in entry",
                        "error": "Missing CPF field",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                failure_count += 1
                continue

            print(
                f"🔄 [{idx}/{total}] Processing CPF: {cpf} ({loja})...",
                end=" ",
                flush=True,
            )

            result = await process_cpf(client, cpf, loja, test_mode, delay)

            if result["success"]:
                print("✅ Success")
                success_count += 1
            else:
                print(f"❌ Failed: {result['message']}")
                failure_count += 1

            results.append(result)

    # Print summary
    print()
    print("=" * 60)
    print("📊 BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total entries: {total}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failure_count}")
    if total > 0:
        success_rate = (success_count / total * 100)
        print(f"Success rate: {success_rate:.1f}%")
    else:
        print("Success rate: N/A")
    print()

    # Write results to file if specified
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_data = {
            "processed_at": datetime.now().isoformat(),
            "input_file": str(input_file),
            "test_mode": test_mode,
            "total_entries": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Results written to: {output_file}")
        except Exception as exc:
            print(f"⚠️  Failed to write results file: {exc}")

    # Exit with error code if any failures
    if failure_count > 0:
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process CPF batch through FoKS NFA endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "/Users/dnigga/Documents/FBP_Backend/data_input_final"
        ),
        help=(
            "Path to input JSON file "
            "(default: FBP_Backend/data_input_final)"
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (sets test=True for all requests)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write results JSON file",
    )
    parser.add_argument(
        "--foks-url",
        type=str,
        default=FOKS_BASE_URL,
        help=f"FoKS base URL (default: {FOKS_BASE_URL})",
    )

    args = parser.parse_args()

    # Update global endpoint if custom URL provided
    global FOKS_NFA_ENDPOINT
    if args.foks_url != FOKS_BASE_URL:
        FOKS_NFA_ENDPOINT = f"{args.foks_url.rstrip('/')}/tasks/nfa"

    # Run async processing
    asyncio.run(
        process_batch(
            input_file=args.input,
            test_mode=args.test,
            delay=args.delay,
            output_file=args.output,
        )
    )


if __name__ == "__main__":
    main()
