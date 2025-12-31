#!/usr/bin/env python3
"""
Script to add new CPF values to cpf_batch_list.json
Extracts CPFs from images or accepts CPF values directly.
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Set

# File path
CPF_FILE = Path(__file__).parent / "cpf_batch_list.json"


def load_current_cpfs() -> List[str]:
    """Load current CPF list from JSON file."""
    if not CPF_FILE.exists():
        return []
    with open(CPF_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def clean_cpf(cpf: str) -> str:
    """Remove formatting from CPF (dots, dashes, spaces)."""
    return re.sub(r'[.\-\s]', '', cpf.strip())


def validate_cpf_format(cpf: str) -> bool:
    """Validate CPF is 11 digits."""
    cleaned = clean_cpf(cpf)
    return len(cleaned) == 11 and cleaned.isdigit()


def add_cpfs_to_list(new_cpfs: List[str], remove_duplicates: bool = True, sort: bool = True) -> dict:
    """
    Add new CPFs to the list.
    
    Args:
        new_cpfs: List of CPF strings (can be formatted or unformatted)
        remove_duplicates: Whether to remove duplicates
        sort: Whether to sort the final list
        
    Returns:
        Dictionary with stats: {'added': int, 'total_before': int, 'total_after': int, 'duplicates': int}
    """
    # Load current
    current_cpfs = load_current_cpfs()
    total_before = len(current_cpfs)
    
    # Clean and validate new CPFs
    cleaned_new = []
    for cpf in new_cpfs:
        cleaned = clean_cpf(cpf)
        if validate_cpf_format(cleaned):
            cleaned_new.append(cleaned)
        else:
            print(f"Warning: Invalid CPF format '{cpf}' (must be 11 digits), skipping", file=sys.stderr)
    
    # Combine
    if remove_duplicates:
        all_cpfs = list(set(current_cpfs + cleaned_new))
    else:
        all_cpfs = current_cpfs + cleaned_new
    
    # Sort if requested
    if sort:
        all_cpfs.sort()
    
    # Write back
    with open(CPF_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_cpfs, f, indent=2, ensure_ascii=False)
    
    total_after = len(all_cpfs)
    added = total_after - total_before
    duplicates = len(cleaned_new) - added
    
    return {
        'added': added,
        'total_before': total_before,
        'total_after': total_after,
        'duplicates': duplicates,
        'invalid': len(new_cpfs) - len(cleaned_new)
    }


def extract_cpfs_from_text(text: str) -> List[str]:
    """Extract CPF patterns from text (supports various formats)."""
    # Pattern for CPF: XXX.XXX.XXX-XX or XXXXXXXXXXX
    patterns = [
        r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b',  # Formatted: 123.456.789-00
        r'\b\d{11}\b',  # Unformatted: 12345678900
    ]
    
    cpfs = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        cpfs.extend(matches)
    
    return cpfs


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add CPF values to batch list")
    parser.add_argument('cpfs', nargs='*', help='CPF values to add (formatted or unformatted)')
    parser.add_argument('--file', type=Path, help='File containing CPFs (one per line or JSON array)')
    parser.add_argument('--no-dedup', action='store_true', help='Do not remove duplicates')
    parser.add_argument('--no-sort', action='store_true', help='Do not sort the list')
    
    args = parser.parse_args()
    
    new_cpfs = []
    
    # Collect CPFs from command line arguments
    if args.cpfs:
        new_cpfs.extend(args.cpfs)
    
    # Collect CPFs from file
    if args.file and args.file.exists():
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Try JSON first
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    new_cpfs.extend(data)
                else:
                    new_cpfs.extend(extract_cpfs_from_text(content))
            except json.JSONDecodeError:
                # Treat as text, extract CPFs
                new_cpfs.extend(extract_cpfs_from_text(content))
    
    if not new_cpfs:
        print("No CPFs provided. Use --help for usage.", file=sys.stderr)
        sys.exit(1)
    
    # Add CPFs
    result = add_cpfs_to_list(
        new_cpfs,
        remove_duplicates=not args.no_dedup,
        sort=not args.no_sort
    )
    
    print(f"Added {result['added']} new CPFs")
    print(f"Total before: {result['total_before']}, Total after: {result['total_after']}")
    if result['duplicates'] > 0:
        print(f"Skipped {result['duplicates']} duplicates")
    if result['invalid'] > 0:
        print(f"Skipped {result['invalid']} invalid CPFs")
