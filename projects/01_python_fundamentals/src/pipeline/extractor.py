"""
Pipeline Extraction Module.
Extracts transaction records from CSV, JSON, or SQLite sources.
"""

import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("pipeline.extractor")

class DataExtractor:
    """Handles data extraction from heterogeneous raw file sources."""

    def extract_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        if not file_path.exists():
            logger.error(f"CSV source file {file_path} does not exist.")
            return []

        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
        logger.info(f"Extracted {len(records)} records from CSV: {file_path}")
        return records

    def extract_json(self, file_path: Path) -> List[Dict[str, Any]]:
        if not file_path.exists():
            logger.error(f"JSON source file {file_path} does not exist.")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Extracted {len(data)} records from JSON: {file_path}")
        return data
