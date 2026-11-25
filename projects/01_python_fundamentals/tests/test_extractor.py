"""Unit tests for Pipeline DataExtractor."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src/pipeline"))

from extractor import DataExtractor

def test_extract_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("transaction_id,amount\nT1,100\nT2,200\n", encoding="utf-8")

    extractor = DataExtractor()
    records = extractor.extract_csv(csv_file)
    assert len(records) == 2
    assert records[0]["transaction_id"] == "T1"
