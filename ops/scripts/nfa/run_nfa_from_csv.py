#!/usr/bin/env python3
"""
Run NFA automation for CPF values from CSV file.

This script:
1. Reads CPF values from CSV file
2. Extracts unique CPFs
3. Runs NFA automation for specified date range
4. Logs CPF associations for reference

Note: The NFA automation uses 'matrícula' (not CPF) to query NFAs.
This script processes all NFAs for the date range and logs CPF info.
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Set

def extract_cpfs_from_csv(csv_path: Path) -> List[str]:
    """Extract unique CPF values from CSV file."""
    cpfs: Set[str] = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                cpf = row[3].strip()  # CPF is in column 4 (index 3)
                if cpf and cpf.replace('.', '').replace('-', '').isdigit():
                    # Clean CPF format (remove dots and dashes for consistency)
                    cpf_clean = cpf.replace('.', '').replace('-', '')
                    if len(cpf_clean) == 11:  # Valid CPF length
                        cpfs.add(cpf)  # Keep original format for logging
    
    return sorted(list(cpfs))

def run_nfa_automation(
    from_date: str,
    to_date: str,
    matricula: str,
    max_nfas: int = 100
) -> dict:
    """Run NFA automation via API."""
    url = "http://localhost:8000/tasks/run"
    
    payload = {
        "type": "nfa_atf",
        "args": {
            "from_date": from_date,
            "to_date": to_date,
            "matricula": matricula,
            "max_nfas": max_nfas,
            "download_dar": True  # Both downloads always execute now
        }
    }
    
    cmd = [
        "curl",
        "-X", "POST",
        url,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload),
        "-s"  # Silent mode
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": f"API call failed: {e.stderr}"}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON response: {e}"}

def main():
    parser = argparse.ArgumentParser(
        description="Run NFA automation for CPF values from CSV"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to CSV file with CPF values"
    )
    parser.add_argument(
        "--from-date",
        type=str,
        required=True,
        help="Start date (dd/mm/yyyy)"
    )
    parser.add_argument(
        "--to-date",
        type=str,
        required=True,
        help="End date (dd/mm/yyyy)"
    )
    parser.add_argument(
        "--matricula",
        type=str,
        default="1595504",
        help="Matrícula number (default: 1595504)"
    )
    parser.add_argument(
        "--max-nfas",
        type=int,
        default=100,
        help="Maximum number of NFAs to process (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    args = parser.parse_args()
    
    # Extract CPFs from CSV
    print(f"Reading CPF values from: {args.csv}")
    cpfs = extract_cpfs_from_csv(args.csv)
    print(f"Found {len(cpfs)} unique CPF values")
    
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Date Range: {args.from_date} to {args.to_date}")
        print(f"Matrícula: {args.matricula}")
        print(f"Max NFAs: {args.max_nfas}")
        print(f"CPFs to process: {len(cpfs)}")
        print("\nFirst 10 CPFs:")
        for cpf in cpfs[:10]:
            print(f"  - {cpf}")
        if len(cpfs) > 10:
            print(f"  ... and {len(cpfs) - 10} more")
        return
    
    # Run NFA automation
    print(f"\nRunning NFA automation:")
    print(f"  Date Range: {args.from_date} to {args.to_date}")
    print(f"  Matrícula: {args.matricula}")
    print(f"  Max NFAs: {args.max_nfas}")
    print(f"  CPF Reference Count: {len(cpfs)}")
    
    result = run_nfa_automation(
        from_date=args.from_date,
        to_date=args.to_date,
        matricula=args.matricula,
        max_nfas=args.max_nfas
    )
    
    # Print results
    print("\n=== RESULTS ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if result.get("success"):
        payload = result.get("payload", {})
        processed = payload.get("processed_count", 0)
        print(f"\n✅ Successfully processed {processed} NFA(s)")
        print(f"📁 Output directory: /Users/dnigga/Downloads/NFA_Outputs/")
    else:
        print(f"\n❌ Error: {result.get('payload', {}).get('message', 'Unknown error')}")

if __name__ == "__main__":
    main()

