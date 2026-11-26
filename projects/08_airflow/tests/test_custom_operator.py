"""
Test Suite: test_custom_operator.py
===================================

PURPOSE:
    Unit test suite for `CustomETLOperator` and `DataQualityOperator`.

CONCEPTS COVERED:
    1. Direct unit testing of Airflow BaseOperator subclasses without running scheduler
    2. Mocking execution context dictionaries
    3. Asserting operator output artifacts and XCom metadata return values
    4. Asserting `AirflowException` throwing under data quality circuit breaker triggers

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock
import pytest

from airflow.exceptions import AirflowException
from src.operators.custom_etl_operator import CustomETLOperator
from src.operators.data_quality_operator import DataQualityOperator


def test_custom_etl_operator_execution(tmp_path):
    """Test execution of CustomETLOperator writing JSON payload to disk."""
    out_file = str(tmp_path / "test_extract.json")

    op = CustomETLOperator(
        task_id="test_etl_task",
        http_conn_id="http_custom_api",
        endpoint="api/v1/orders",
        output_path=out_file,
        execution_date="2024-01-15",
    )

    mock_context = {
        "ds": "2024-01-15",
        "ti": MagicMock(),
    }

    result = op.execute(context=mock_context)

    assert os.path.exists(out_file)
    assert result["output_record_count"] == 250
    assert result["execution_date"] == "2024-01-15"

    with open(out_file, "r") as f:
        data = json.load(f)
        assert len(data) == 250
        assert data[0]["amount_cents"] == 15000


def test_data_quality_operator_success(tmp_path):
    """Test DataQualityOperator passing valid file checks."""
    test_file = str(tmp_path / "valid_data.json")
    sample_data = [
        {"id": 1, "status": "ACTIVE", "amount": 100},
        {"id": 2, "status": "ACTIVE", "amount": 200},
    ]
    with open(test_file, "w") as f:
        json.dump(sample_data, f)

    op = DataQualityOperator(
        task_id="test_dq_task",
        file_path=test_file,
        min_row_count=1,
        max_row_count=10,
        required_columns=["id", "status"],
        non_null_columns=["id"],
        execution_date="2024-01-15",
    )

    result = op.execute(context={"ds": "2024-01-15"})
    assert result["status"] == "PASSED"
    assert result["row_count"] == 2


def test_data_quality_operator_failure_threshold(tmp_path):
    """Test DataQualityOperator raising AirflowException when min_row_count is not met."""
    test_file = str(tmp_path / "empty_data.json")
    with open(test_file, "w") as f:
        json.dump([], f)

    op = DataQualityOperator(
        task_id="test_dq_failure_task",
        file_path=test_file,
        min_row_count=5,  # Requires at least 5 rows
        execution_date="2024-01-15",
    )

    with pytest.raises(AirflowException) as exc_info:
        op.execute(context={"ds": "2024-01-15"})

    assert "Row count threshold violation" in str(exc_info.value)
