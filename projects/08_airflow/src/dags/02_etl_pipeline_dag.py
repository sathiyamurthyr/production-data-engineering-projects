"""
DAG: 02_etl_pipeline_dag.py
============================

PURPOSE:
    Production ETL pipeline demonstrating a complete Extract → Transform → Load
    workflow with conditional branching, error handling, and data quality gates.

CONCEPTS COVERED:
    1. Full ETL pattern (Extract, Transform, Load phases as separate task groups)
    2. BranchPythonOperator — conditional routing based on runtime logic
    3. TaskGroup — visually grouping related tasks in the Airflow UI
    4. TriggerRule — controlling when a task runs based on upstream state
    5. XCom — passing dataset metadata (row counts, file paths) between tasks
    6. Variable — reading runtime config from Airflow Variables
    7. on_success_callback / on_failure_callback — lifecycle hooks

BUSINESS USE CASE:
    Daily Sales ETL: Extract yesterday's sales transactions from an SFTP server,
    validate the file, transform raw CSVs into a clean schema, apply business rules
    (discounts, tax), and load into the data warehouse. Branch to an alert task
    if data quality checks fail. Send a Slack notification on completion.

DAG FLOW:
    start
      └── extract_sales_data
            └── validate_raw_file
                  ├── [data_ok] ──► transform_data ──► apply_business_rules ──► load_to_warehouse ──► end
                  └── [data_bad] ─► alert_data_quality_failure ──────────────────────────────────────► end

PERFORMANCE NOTES:
    - TaskGroups are purely visual — no execution overhead
    - Branch tasks must return exactly one downstream task_id
    - ALL downstream tasks of a branch that are NOT chosen get SKIPPED
    - Use trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS on the end task
      so it still completes even if a branch path was skipped

COMMON MISTAKES:
    1. Forgetting trigger_rule on tasks downstream of a branch (they get stuck in SKIPPED)
    2. Pushing large DataFrames through XCom (use file paths or S3 keys instead)
    3. Not clearing task state before re-running a branching DAG manually
    4. Using PythonOperator for CPU-heavy work that should run on Spark/Dask

INTERVIEW QUESTIONS:
    Q: How does BranchPythonOperator work?
    A: It calls a Python function that returns the task_id(s) to execute next.
       All other downstream tasks are automatically SKIPPED. You must handle
       trigger_rule carefully on tasks that merge the branches back together.

    Q: What is TriggerRule and when do you use it?
    A: TriggerRule controls when a task is eligible to run based on the state
       of its upstream tasks. Common values:
         - ALL_SUCCESS (default): all parents succeeded
         - ALL_FAILED: all parents failed
         - ONE_SUCCESS: at least one parent succeeded
         - NONE_FAILED_MIN_ONE_SUCCESS: no failures, at least one success (ideal for branch merges)
         - ALL_DONE: all parents finished regardless of state

    Q: What are TaskGroups?
    A: Logical groupings of tasks that collapse into a single node in the Airflow UI.
       They do NOT affect execution order, only visual organization. Introduced in Airflow 2.0
       to replace SubDAGs which had performance and concurrency issues.

    Q: What is the difference between SubDAG and TaskGroup?
    A: SubDAGs were pre-2.0 — they created child DAG objects with their own scheduler
       logic, causing concurrency issues and deadlocks. TaskGroups in 2.0+ are purely
       visual groupings within one DAG, solving all SubDAG problems.

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DEFAULT ARGS
# ---------------------------------------------------------------------------
default_args: dict = {
    "owner": "data-engineering-diaries",
    "email_on_failure": True,
    "email_on_retry": False,
    "email": ["data-team@company.com"],
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "retry_exponential_backoff": True,   # Doubles delay on each retry
    "max_retry_delay": timedelta(hours=1),
    "execution_timeout": timedelta(hours=2),
}

# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------

def on_success_callback(context: dict) -> None:
    """Called when the DAG completes successfully. Log and/or notify."""
    dag_id = context["dag"].dag_id
    execution_date = context["ds"]
    log.info("[SUCCESS CALLBACK] DAG '%s' completed for execution date %s", dag_id, execution_date)
    # In production: send Slack/Teams/PagerDuty notification here


def on_failure_callback(context: dict) -> None:
    """Called when a task fails. Log error context for debugging."""
    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id
    execution_date = context["ds"]
    exception = context.get("exception", "Unknown error")
    log.error(
        "[FAILURE CALLBACK] Task '%s' in DAG '%s' failed on %s. Error: %s",
        task_id, dag_id, execution_date, exception,
    )


# ---------------------------------------------------------------------------
# EXTRACT PHASE
# ---------------------------------------------------------------------------

def extract_sales_data(**context: dict) -> dict[str, Any]:
    """
    Simulate extracting sales data from an SFTP server.

    In production, this would:
    1. Use SSHHook / SFTPHook to connect to the source server
    2. Download yesterday's sales file (e.g., sales_2024-01-01.csv)
    3. Upload it to S3/GCS staging area
    4. Return metadata (file path, row count estimate, file size)

    Returns:
        dict: Metadata pushed to XCom for downstream tasks
    """
    execution_date: str = context["ds"]
    log.info("Extracting sales data for %s...", execution_date)

    # Simulate file download
    file_path = f"/tmp/sales_{execution_date.replace('-', '')}.csv"
    row_count = random.randint(1000, 50000)  # Simulated row count

    # Read environment config from Airflow Variable (set via UI or CLI)
    # airflow variables set etl_config '{"source_bucket": "s3://raw-data", "batch_size": 10000}'
    etl_config_raw: str = Variable.get("etl_config", default_var='{"source_bucket": "s3://raw-data", "batch_size": 10000}')
    etl_config: dict = json.loads(etl_config_raw)

    log.info("ETL config: %s", etl_config)
    log.info("Simulated file path: %s | Row count: %d", file_path, row_count)

    metadata = {
        "file_path": file_path,
        "row_count": row_count,
        "execution_date": execution_date,
        "source_bucket": etl_config.get("source_bucket"),
    }
    return metadata  # Auto-pushed to XCom as return_value


def validate_raw_file(**context: dict) -> None:
    """
    Validate the extracted raw file meets quality thresholds.

    Checks:
    - File exists (non-zero size)
    - Row count within expected range (> min_rows threshold)
    - Schema columns present
    - No null primary keys
    """
    metadata: dict = context["ti"].xcom_pull(
        task_ids="extract.extract_sales_data",
        key="return_value",
    )
    if not metadata:
        raise ValueError("No metadata found from extract_sales_data. Extraction may have failed.")

    row_count: int = metadata["row_count"]
    file_path: str = metadata["file_path"]
    min_rows: int = int(Variable.get("min_expected_rows", default_var=500))

    log.info("Validating file: %s | Rows: %d | Min required: %d", file_path, row_count, min_rows)

    # Push validation result for branch decision
    is_valid = row_count >= min_rows
    context["ti"].xcom_push(key="is_valid", value=is_valid)
    context["ti"].xcom_push(key="row_count", value=row_count)

    if not is_valid:
        log.warning("Row count %d below minimum %d. Pipeline will route to alert.", row_count, min_rows)
    else:
        log.info("Validation PASSED. Proceeding to transform phase.")


# ---------------------------------------------------------------------------
# BRANCH FUNCTION
# ---------------------------------------------------------------------------

def route_on_quality(**context: dict) -> str:
    """
    BranchPythonOperator callable.
    Returns the task_id of the next task to execute.

    Returns:
        str: Either 'transform.transform_data' or 'alert_data_quality_failure'
    """
    is_valid: bool = context["ti"].xcom_pull(
        task_ids="extract.validate_raw_file",
        key="is_valid",
    )
    if is_valid:
        log.info("Branch: data quality OK → proceeding to transform")
        return "transform.transform_data"  # Note: includes TaskGroup prefix
    else:
        log.warning("Branch: data quality FAILED → routing to alert")
        return "alert_data_quality_failure"


# ---------------------------------------------------------------------------
# TRANSFORM PHASE
# ---------------------------------------------------------------------------

def transform_data(**context: dict) -> dict[str, Any]:
    """
    Transform raw sales data into cleaned, analytics-ready schema.

    In production, this would:
    1. Read the raw CSV from S3 staging
    2. Apply schema mapping (rename columns, cast types)
    3. Deduplicate records
    4. Handle nulls and outliers
    5. Write cleaned Parquet to S3 transform layer

    Returns:
        dict: Transformed dataset metadata
    """
    metadata: dict = context["ti"].xcom_pull(
        task_ids="extract.extract_sales_data",
        key="return_value",
    )
    log.info("Transforming data from: %s", metadata["file_path"])

    # Simulate transformation
    transformed_rows = int(metadata["row_count"] * 0.98)  # 2% deduplication
    transformed_path = metadata["file_path"].replace("/tmp/", "/tmp/transformed_")

    transform_result = {
        "transformed_path": transformed_path,
        "input_rows": metadata["row_count"],
        "output_rows": transformed_rows,
        "deduplication_pct": 2.0,
    }
    log.info("Transform complete: %d → %d rows", metadata["row_count"], transformed_rows)
    return transform_result


def apply_business_rules(**context: dict) -> dict[str, Any]:
    """
    Apply domain-specific business rules to the transformed dataset.

    Business rules applied:
    - Calculate net sales after discounts (10% discount on orders > $1000)
    - Apply regional tax rates
    - Classify sales tiers (small/medium/large)
    - Flag high-value customers

    Returns:
        dict: Enriched dataset metadata
    """
    transform_result: dict = context["ti"].xcom_pull(
        task_ids="transform.transform_data",
        key="return_value",
    )
    log.info("Applying business rules to %d rows...", transform_result["output_rows"])

    # Simulate business rule application
    enriched_path = transform_result["transformed_path"].replace("transformed_", "enriched_")
    enriched_result = {
        **transform_result,
        "enriched_path": enriched_path,
        "business_rules_applied": ["discount", "tax", "tier_classification"],
        "high_value_customers": random.randint(50, 500),
    }
    log.info("Business rules applied. High-value customers flagged: %d",
             enriched_result["high_value_customers"])
    return enriched_result


# ---------------------------------------------------------------------------
# LOAD PHASE
# ---------------------------------------------------------------------------

def load_to_warehouse(**context: dict) -> None:
    """
    Load enriched data into the data warehouse (Snowflake / BigQuery / Redshift).

    In production, this would:
    1. Use a warehouse-specific hook (SnowflakeHook, BigQueryHook)
    2. Copy Parquet files from S3 into a staging table
    3. Run MERGE / UPSERT logic to update the production table
    4. Update pipeline metadata / audit table with row counts
    5. Trigger dbt models or downstream DAGs

    Pattern: COPY INTO → MERGE → ANALYZE (statistics update)
    """
    enriched_result: dict = context["ti"].xcom_pull(
        task_ids="transform.apply_business_rules",
        key="return_value",
    )
    log.info("Loading %d rows to data warehouse...", enriched_result["output_rows"])

    # Simulate load
    log.info("COPY INTO raw.sales_transactions FROM '%s'", enriched_result["enriched_path"])
    log.info("MERGE INTO prod.sales_facts USING staging.sales_transactions ON id = id")
    log.info("Load complete. %d rows written to prod.sales_facts.", enriched_result["output_rows"])


# ---------------------------------------------------------------------------
# ALERT / ERROR PATH
# ---------------------------------------------------------------------------

def alert_data_quality_failure(**context: dict) -> None:
    """
    Alert task executed when data quality check fails.
    Sends a PagerDuty / Slack alert and writes to the incident log table.
    """
    execution_date: str = context["ds"]
    row_count: int = context["ti"].xcom_pull(
        task_ids="extract.validate_raw_file",
        key="row_count",
    ) or 0

    log.error(
        "[DQ ALERT] Sales ETL for %s failed data quality check. "
        "Row count: %d. Manual intervention required.",
        execution_date,
        row_count,
    )
    # In production: call PagerDuty API, post to #data-incidents Slack channel


# ---------------------------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------------------------
with DAG(
    dag_id="02_etl_pipeline",
    description="Full ETL pipeline: Extract → Validate → Branch → Transform → Load",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 5 * * *",   # Daily at 05:00 UTC (before business hours)
    catchup=False,
    max_active_runs=1,
    tags=["etl", "sales", "production", "data-engineering-diaries"],
    on_success_callback=on_success_callback,
    on_failure_callback=on_failure_callback,
    doc_md="""
## Sales ETL Pipeline

Full Extract → Transform → Load pipeline for daily sales transactions.

### Architecture
```
start → extract_group → validate → branch → transform_group → load → end
                                        └──► alert → end
```

### Data Quality Gate
- Minimum row threshold: Airflow Variable `min_expected_rows` (default: 500)
- ETL configuration: Airflow Variable `etl_config` (JSON)

### Schedule: Daily 05:00 UTC
    """,
) as dag:

    start = EmptyOperator(task_id="start")

    # -----------------------------------------------------------------------
    # EXTRACT GROUP — visually collapses in Airflow UI
    # -----------------------------------------------------------------------
    with TaskGroup(group_id="extract", tooltip="Extract and validate raw sales data") as extract_group:

        extract_sales_data_task = PythonOperator(
            task_id="extract_sales_data",
            python_callable=extract_sales_data,
            doc_md="Download sales CSV from SFTP → upload to S3 staging.",
        )

        validate_raw_file_task = PythonOperator(
            task_id="validate_raw_file",
            python_callable=validate_raw_file,
            doc_md="Validate row count, schema, and null checks on raw file.",
        )

        extract_sales_data_task >> validate_raw_file_task

    # -----------------------------------------------------------------------
    # BRANCH OPERATOR
    # -----------------------------------------------------------------------
    branch = BranchPythonOperator(
        task_id="branch_on_quality",
        python_callable=route_on_quality,
        doc_md="Route pipeline based on data quality check outcome.",
    )

    # -----------------------------------------------------------------------
    # ALERT TASK (bad data path)
    # -----------------------------------------------------------------------
    alert_task = PythonOperator(
        task_id="alert_data_quality_failure",
        python_callable=alert_data_quality_failure,
        doc_md="Send DQ failure alert via PagerDuty and Slack.",
    )

    # -----------------------------------------------------------------------
    # TRANSFORM GROUP (good data path)
    # -----------------------------------------------------------------------
    with TaskGroup(group_id="transform", tooltip="Transform and enrich sales data") as transform_group:

        transform_task = PythonOperator(
            task_id="transform_data",
            python_callable=transform_data,
            doc_md="Clean, deduplicate, and reformat raw sales data.",
        )

        business_rules_task = PythonOperator(
            task_id="apply_business_rules",
            python_callable=apply_business_rules,
            doc_md="Apply discounts, taxes, and tier classification.",
        )

        transform_task >> business_rules_task

    # -----------------------------------------------------------------------
    # LOAD TASK
    # -----------------------------------------------------------------------
    load_task = PythonOperator(
        task_id="load_to_warehouse",
        python_callable=load_to_warehouse,
        doc_md="COPY + MERGE enriched data into prod.sales_facts.",
    )

    # -----------------------------------------------------------------------
    # BASH TASK: Update pipeline run metadata table
    # -----------------------------------------------------------------------
    update_metadata = BashOperator(
        task_id="update_pipeline_metadata",
        bash_command=(
            "echo \"INSERT INTO pipeline_runs "
            "(dag_id, execution_date, status, updated_at) "
            "VALUES ('{{ dag.dag_id }}', '{{ ds }}', 'SUCCESS', NOW());\" "
            "| tee /tmp/pipeline_metadata_{{ ds_nodash }}.sql"
        ),
        doc_md="Log successful pipeline run to the audit/metadata table.",
    )

    # -----------------------------------------------------------------------
    # END (trigger_rule ensures it runs even when one branch was SKIPPED)
    # -----------------------------------------------------------------------
    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        doc_md="Pipeline exit. Runs regardless of which branch was taken.",
    )

    # -----------------------------------------------------------------------
    # TASK DEPENDENCIES
    # -----------------------------------------------------------------------
    start >> extract_group >> branch

    # Happy path
    branch >> transform_group >> load_task >> update_metadata >> end

    # Failure / alert path
    branch >> alert_task >> end
