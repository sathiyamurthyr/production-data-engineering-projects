"""
Utility: airflow_utils.py
==========================

PURPOSE:
    Reusable helper functions for Airflow DAGs, custom operators, and callbacks.
    Provides standard path formatters, Variable parsing with fallbacks, and execution context validators.

CONCEPTS COVERED:
    1. Safe Airflow Variable parsing (protecting DAG parsing phase from missing variable exceptions)
    2. Standardized Hive/S3 partition path generation (`year=YYYY/month=MM/day=DD`)
    3. DAG run context validation
    4. Execution summary text formatting

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from airflow.models import Variable

log = logging.getLogger(__name__)


def get_airflow_variable_json(key: str, default_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Safely retrieves an Airflow Variable containing JSON and returns it as a dictionary.
    Includes a fallback dictionary to prevent DAG parsing failures if the Variable is missing.

    Args:
        key (str): Airflow Variable name
        default_dict (Optional[Dict[str, Any]]): Fallback dictionary if key not found

    Returns:
        Dict[str, Any]: Parsed JSON content as dictionary
    """
    if default_dict is None:
        default_dict = {}

    try:
        raw_val = Variable.get(key, default_var=None)
        if raw_val is None:
            log.warning("Airflow Variable '%s' not found in Metadata DB. Using default fallback dictionary.", key)
            return default_dict
        return json.loads(raw_val)
    except json.JSONDecodeError as err:
        log.error("Failed to parse JSON for Airflow Variable '%s': %s. Returning default fallback.", key, str(err))
        return default_dict
    except Exception as err:
        log.warning("Error fetching Airflow Variable '%s': %s. Returning default fallback.", key, str(err))
        return default_dict


def build_s3_partition_path(base_bucket: str, table_name: str, execution_date_str: str) -> str:
    """
    Generates a standardized Hive-style S3 partition path for a given execution date.

    Example:
        `build_s3_partition_path("s3://analytics-lake", "sales_facts", "2024-03-15")`
        Returns: `"s3://analytics-lake/sales_facts/year=2024/month=03/day=15"`

    Args:
        base_bucket (str): Base bucket URI (e.g., 's3://my-data-lake')
        table_name (str): Target table or topic name
        execution_date_str (str): Date string in 'YYYY-MM-DD' format

    Returns:
        str: Fully-qualified Hive partition path
    """
    dt = datetime.strptime(execution_date_str, "%Y-%m-%d")
    bucket = base_bucket.rstrip("/")
    partition = f"year={dt.strftime('%Y')}/month={dt.strftime('%m')}/day={dt.strftime('%d')}"
    return f"{bucket}/{table_name}/{partition}"


def validate_dag_run_context(context: Dict[str, Any], required_keys: Optional[List[str]] = None) -> None:
    """
    Validates that essential Airflow context parameters exist in the callable kwargs.

    Args:
        context (Dict[str, Any]): Airflow execution context dictionary
        required_keys (Optional[List[str]]): List of context keys required (defaults to ['ds', 'ti', 'dag'])
    """
    if required_keys is None:
        required_keys = ["ds", "ti", "dag"]

    missing = [k for k in required_keys if k not in context]
    if missing:
        raise KeyError(f"Invalid execution context: missing required keys {missing}")


def format_execution_summary(context: Dict[str, Any], metrics: Dict[str, Any]) -> str:
    """
    Formats a clean execution summary string for logging or Slack notifications.

    Args:
        context (Dict[str, Any]): Airflow task execution context
        metrics (Dict[str, Any]): Custom metrics dictionary

    Returns:
        str: Multi-line formatted markdown string
    """
    dag_id = context["dag"].dag_id
    task_id = context["ti"].task_id
    ds = context["ds"]
    duration = round(context["ti"].duration, 2) if context["ti"].duration else 0.0

    lines = [
        f"📊 **Pipeline Execution Summary**",
        f"- **DAG ID**: `{dag_id}`",
        f"- **Task ID**: `{task_id}`",
        f"- **Execution Date**: `{ds}`",
        f"- **Duration**: `{duration}s`",
        f"- **Metrics**:",
    ]
    for k, v in metrics.items():
        lines.append(f"  - `{k}`: `{v}`")

    return "\n".join(lines)
