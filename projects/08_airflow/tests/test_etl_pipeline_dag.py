"""
Test Suite: test_etl_pipeline_dag.py
====================================

PURPOSE:
    Unit test suite validating structure, task dependencies, and callables of `02_etl_pipeline_dag.py`.

CONCEPTS COVERED:
    1. Inspection of DAG task tree structure and task counts
    2. Unit testing PythonOperator callables with mocked task instance context
    3. Branching logic assertion under different XCom return values

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock
import pytest

from airflow.models import DagBag

DAG_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "dags"))

@pytest.fixture(scope="module")
def etl_dag():
    dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
    return dag_bag.get_dag("02_etl_pipeline")


def test_etl_dag_structure(etl_dag):
    """Verify that 02_etl_pipeline loaded correctly with expected task structure."""
    assert etl_dag is not None
    assert etl_dag.dag_id == "02_etl_pipeline"
    assert etl_dag.schedule_interval == "0 5 * * *"

    expected_tasks = {
        "start",
        "extract.extract_sales_data",
        "extract.validate_raw_file",
        "branch_on_quality",
        "alert_data_quality_failure",
        "transform.transform_data",
        "transform.apply_business_rules",
        "load_to_warehouse",
        "update_pipeline_metadata",
        "end",
    }
    actual_tasks = set(etl_dag.task_ids)
    assert expected_tasks.issubset(actual_tasks), f"Missing expected tasks. Found: {actual_tasks}"


def test_branch_logic_valid():
    """Test route_on_quality callable when data is valid."""
    from src.dags.02_etl_pipeline_dag import route_on_quality

    mock_ti = MagicMock()
    mock_ti.xcom_pull.return_value = True  # is_valid = True
    context = {"ti": mock_ti}

    selected_branch = route_on_quality(**context)
    assert selected_branch == "transform.transform_data"


def test_branch_logic_invalid():
    """Test route_on_quality callable when data quality fails."""
    from src.dags.02_etl_pipeline_dag import route_on_quality

    mock_ti = MagicMock()
    mock_ti.xcom_pull.return_value = False  # is_valid = False
    context = {"ti": mock_ti}

    selected_branch = route_on_quality(**context)
    assert selected_branch == "alert_data_quality_failure"
