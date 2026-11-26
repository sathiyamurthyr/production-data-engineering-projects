"""
JSON Extractor module for nested JSON and JSON Lines (JSONL) documents.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.extractors.base_extractor import BaseExtractor, ExtractionError


class JSONExtractor(BaseExtractor):
    """Extractor for standard JSON files and JSON Lines (ndjson) files."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize JSON Extractor.

        Config Keys:
            path (str): File path to JSON file.
            orient (str): Expected JSON orientation ('records', 'split', 'index', etc.).
            lines (bool): True if reading line-delimited JSON (JSONL).
            flatten_nested (bool): Whether to auto-normalize nested fields.
        """
        super().__init__(config)
        self.file_path = Path(config.get("path", ""))
        self.orient = config.get("orient", "records")
        self.lines = config.get("lines", False)
        self.flatten_nested = config.get("flatten_nested", True)

    def extract(self) -> pd.DataFrame:
        """
        Extract JSON content into a pandas DataFrame.

        Returns:
            pd.DataFrame: Tabular representation of JSON data.

        Raises:
            ExtractionError: If file is missing or invalid JSON.
        """
        if not self.file_path.exists():
            msg = f"JSON file not found at path: {self.file_path}"
            self.logger.error(msg)
            raise ExtractionError(msg)

        try:
            self.logger.info(f"Extracting JSON dataset from {self.file_path}")

            if self.lines:
                df = pd.read_json(self.file_path, lines=True)
            else:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                if self.flatten_nested and isinstance(raw_data, list):
                    df = pd.json_normalize(raw_data)
                elif isinstance(raw_data, list):
                    df = pd.DataFrame(raw_data)
                elif isinstance(raw_data, dict):
                    if self.flatten_nested:
                        df = pd.json_normalize(raw_data)
                    else:
                        df = pd.DataFrame([raw_data])
                else:
                    raise ValueError(f"Unrecognized JSON payload structure: {type(raw_data)}")

            self.logger.info(f"Successfully extracted {len(df)} JSON records.")
            return df

        except Exception as e:
            msg = f"Failed extracting JSON file {self.file_path}: {str(e)}"
            self.logger.error(msg)
            raise ExtractionError(msg) from e
