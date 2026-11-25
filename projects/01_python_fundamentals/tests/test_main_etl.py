"""Integration tests for Mini ETL Pipeline Main Orchestrator."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src/pipeline"))

from main_etl import run_pipeline

def test_run_pipeline_end_to_end():
    p01_dir = Path(__file__).resolve().parent.parent
    status = run_pipeline(p01_dir)
    assert status == 0
    output_file = p01_dir / "output/sales_summary.json"
    assert output_file.exists()
