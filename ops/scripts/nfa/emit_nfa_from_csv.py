#!/usr/bin/env python3
"""
Emit NFAs for CPF values from CSV file.

This script:
1. Reads CPF and LOJA values from CSV file
2. Extracts unique CPF entries (with LOJA association)
3. For each CPF, calls NFA emission automation via FoKS API
4. Logs results with LOJA association
5. Provides progress tracking and summary
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Ensure project root is on sys.path so `ops.*` imports work when executed directly.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# Run in-process to reuse ONE browser session (visual) for the whole batch.
from ops.scripts.nfa.nfa_emit import NFAEmitAutomation  # type: ignore  # noqa: E402


def _load_env_fallback() -> None:
    """
    Best-effort: if NFA_* credentials aren't in env, try to load from FBP_Backend/.env.
    Mirrors backend/app/services/script_runner.py behavior.
    """
    if os.getenv("NFA_USERNAME") and os.getenv("NFA_PASSWORD"):
        return

    fbp_env_path = Path("/Users/dnigga/Documents/FBP_Backend/.env")
    if not fbp_env_path.exists():
        return

    # Try python-dotenv first, fallback to manual parsing.
    try:
        from dotenv import dotenv_values  # type: ignore

        values = dotenv_values(fbp_env_path)
        if not os.getenv("NFA_USERNAME") and values.get("NFA_USERNAME"):
            os.environ["NFA_USERNAME"] = str(values["NFA_USERNAME"])
        if not os.getenv("NFA_PASSWORD") and values.get("NFA_PASSWORD"):
            os.environ["NFA_PASSWORD"] = str(values["NFA_PASSWORD"])
        return
    except Exception:
        pass

    try:
        with open(fbp_env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "NFA_USERNAME" and not os.getenv("NFA_USERNAME"):
                    os.environ["NFA_USERNAME"] = v
                if k == "NFA_PASSWORD" and not os.getenv("NFA_PASSWORD"):
                    os.environ["NFA_PASSWORD"] = v
    except Exception:
        return


def extract_cpf_entries_from_csv(csv_path: Path) -> List[Dict[str, str]]:
    """
    Extract CPF and LOJA entries from CSV file.
    
    Returns list of dicts with 'cpf' and 'loja' keys.
    Keeps all entries (including duplicates) for tracking.
    """
    entries: List[Dict[str, str]] = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader, start=1):
            if len(row) >= 4:
                loja = row[1].strip() if len(row) > 1 else ""
                cpf = row[3].strip() if len(row) > 3 else ""

                if cpf and cpf.replace(".", "").replace("-", "").isdigit():
                    # Clean CPF format (remove dots and dashes)
                    cpf_clean = cpf.replace(".", "").replace("-", "")
                    if len(cpf_clean) == 11:  # Valid CPF length
                        entries.append(
                            {
                                "cpf": cpf,  # Keep original format
                                "cpf_clean": cpf_clean,  # Clean format for API
                                "loja": loja,
                                "row": row_num,
                            }
                        )

    return entries


def get_unique_cpfs(entries: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Get unique CPFs, keeping first occurrence with LOJA.
    
    Returns list of unique CPF entries.
    """
    seen = set()
    unique: List[Dict[str, str]] = []

    for entry in entries:
        cpf_clean = entry["cpf_clean"]
        if cpf_clean not in seen:
            seen.add(cpf_clean)
            unique.append(entry)

    return unique


async def run_batch_in_one_browser(
    *,
    entries: List[Dict[str, str]],
    test_mode: bool,
    delay: float,
    output_dir: str,
    keep_open: bool,
) -> Dict[str, object]:
    """
    Run the entire batch in a single Playwright session:
    - one login
    - one visual browser window (headless=False)
    - emit_one() per CPF
    """
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")
    if not username or not password:
        return {
            "success": False,
            "message": (
                "Missing NFA_USERNAME/NFA_PASSWORD in environment for local run. "
                "Export them or rely on script_runner env loading when using the API."
            ),
            "results": [],
        }

    automation = NFAEmitAutomation(
        username=username,
        password=password,
        cpf=None,
        test_mode=test_mode,
        headless=False,
        output_dir=output_dir,
        keep_open=keep_open,
    )

    await automation.setup()
    await automation.login()

    results: List[Dict[str, object]] = []
    success_count = 0
    failure_count = 0

    for idx, entry in enumerate(entries, 1):
        cpf = entry["cpf"]
        cpf_clean = entry["cpf_clean"]
        loja = entry["loja"]

        print(
            f"[{idx}/{len(entries)}] Emitting CPF: {cpf} (LOJA: {loja})...",
            end=" ",
            flush=True,
        )

        payload = await automation.emit_one(cpf_clean)

        ok = payload.get("status") == "success"
        if ok:
            print("✅ Success")
            success_count += 1
        else:
            print(f"❌ Failed: {payload.get('message', 'Unknown error')}")
            failure_count += 1

        results.append(
            {
                "cpf": cpf,
                "cpf_clean": cpf_clean,
                "loja": loja,
                "row": entry["row"],
                "ok": ok,
                "payload": payload,
                "timestamp": datetime.now().isoformat(),
            }
        )

        if idx < len(entries) and delay > 0:
            await asyncio.sleep(delay)

    # Keep browser open if requested (visual mode)
    if not keep_open:
        try:
            await automation.cleanup()
        except Exception:
            pass

    return {
        "success": failure_count == 0,
        "test_mode": test_mode,
        "total": len(entries),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }

def main():
    parser = argparse.ArgumentParser(
        description="Emit NFAs for CPF values from CSV file"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to CSV file with CPF values"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Test mode (validate form but don't submit)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/Users/dnigga/Downloads/NFA_Outputs",
        help="Directory to save emitted PDFs (default: /Users/dnigga/Downloads/NFA_Outputs)",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        default=True,
        help="Keep the visual browser open at the end (default: true)",
    )
    parser.add_argument(
        "--no-keep-open",
        dest="keep_open",
        action="store_false",
        help="Close the browser at the end",
    )
    parser.add_argument(
        "--max-cpfs",
        type=int,
        default=None,
        help="Maximum number of CPFs to process (default: all)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write results JSON file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    args = parser.parse_args()

    # Best-effort load credentials if not exported in env.
    _load_env_fallback()
    
    # Extract CPF entries from CSV
    print(f"Reading CPF values from: {args.csv}")
    all_entries = extract_cpf_entries_from_csv(args.csv)
    print(f"Found {len(all_entries)} CPF entries in CSV")
    
    # Get unique CPFs
    unique_entries = get_unique_cpfs(all_entries)
    print(f"Found {len(unique_entries)} unique CPF values")
    
    # Limit if max_cpfs specified
    if args.max_cpfs:
        unique_entries = unique_entries[:args.max_cpfs]
        print(f"Limited to first {len(unique_entries)} CPFs")
    
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Test Mode: {args.test}")
        print(f"Delay: {args.delay}s")
        print(f"CPFs to process: {len(unique_entries)}")
        print("\nFirst 10 CPFs:")
        for entry in unique_entries[:10]:
            print(f"  - CPF: {entry['cpf']}, LOJA: {entry['loja']}")
        if len(unique_entries) > 10:
            print(f"  ... and {len(unique_entries) - 10} more")
        return
    
    # Process CPFs (one browser session)
    print(f"\nProcessing {len(unique_entries)} CPF(s):")
    print(f"  Test Mode: {args.test}")
    print(f"  Delay: {args.delay}s")
    print(f"  Output dir: {args.output_dir}")
    print(f"  Keep browser open: {args.keep_open}")
    print()

    run_result = asyncio.run(
        run_batch_in_one_browser(
            entries=unique_entries,
            test_mode=args.test,
            delay=args.delay,
            output_dir=args.output_dir,
            keep_open=args.keep_open,
        )
    )

    # Persist results if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "processed_at": datetime.now().isoformat(),
                        "input_file": str(args.csv),
                        "output_dir": args.output_dir,
                        **run_result,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            print(f"💾 Results written to: {args.output}")
        except Exception as exc:
            print(f"⚠️  Failed to write results file: {exc}")

    if not run_result.get("success", False):
        sys.exit(1)

if __name__ == "__main__":
    main()
