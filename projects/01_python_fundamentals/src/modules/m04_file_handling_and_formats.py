"""
Module 13-16: Exception Handling, File I/O, JSON, and CSV Processing.

Explanation:
Data engineering pipelines must read CSV/JSON safely, manage resource handles using try/except/finally
or context managers, and handle corrupted lines without crashing the entire batch job.

Business Use Case:
Parse incoming JSON files and write validated CSV outputs with robust line-level error isolation.
"""

import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def process_json_to_csv(json_path: Path, output_csv_path: Path) -> int:
    """
    Module 13-16 Production Example: Read JSON array, validate, write CSV summary.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            records: List[Dict[str, Any]] = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Failed to load JSON file {json_path}: {e}")
        raise

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["user_id", "name", "email", "signup_date", "is_active"]
    processed_count = 0

    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            if "user_id" in record and "email" in record:
                writer.writerow({k: record.get(k, "") for k in fieldnames})
                processed_count += 1
            else:
                logger.warning(f"Skipping corrupt user record: {record}")

    return processed_count
