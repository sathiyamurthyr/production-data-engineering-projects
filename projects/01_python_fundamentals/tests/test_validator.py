"""Unit tests for Pipeline DataValidator."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src/pipeline"))

from validator import DataValidator

def test_validator_quarantine(tmp_path):
    q_file = tmp_path / "quarantine.csv"
    validator = DataValidator(q_file)

    raw = [
        {"transaction_id": "T1", "amount": "100.0", "status": "COMPLETED"},
        {"transaction_id": "T2", "amount": "-50.0", "status": "COMPLETED"},
        {"transaction_id": "", "amount": "200.0", "status": "COMPLETED"},
        {"transaction_id": "T4", "amount": "300.0", "status": "FAILED"}
    ]

    valid, invalid = validator.validate_transactions(raw)
    assert len(valid) == 1
    assert len(invalid) == 3
    assert q_file.exists()
