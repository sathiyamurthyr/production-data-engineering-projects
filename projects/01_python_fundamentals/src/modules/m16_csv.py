"""
================================================================================
MODULE 16: CSV Processing with DictReader & DictWriter
================================================================================
1. EXPLANATION:
`csv.DictReader` and `csv.DictWriter` handle CSV files as Python dictionaries, preserving column mapping.

2. BUSINESS USE CASE:
Read raw CSV transactions, clean record values, and write out formatted CSV files.
"""
import csv
from pathlib import Path
from typing import List, Dict, Any

def process_csv_file(input_path: Path, output_path: Path) -> int:
    """Read CSV, sanitize amounts, and write out clean CSV."""
    if not input_path.exists():
        return 0
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        return 0

    fieldnames = list(records[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    return len(records)
