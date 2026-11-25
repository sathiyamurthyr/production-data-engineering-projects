"""
DAG: 04_sensor_dag.py
=====================

PURPOSE:
    Demonstrates Airflow Sensors — a special class of operators that poll for
    a condition and block task execution until the condition is met or times out.
    Sensors are the "wait for external event" primitive in Airflow.

CONCEPTS COVERED:
    1. FileSensor — wait for a file to appear on the filesystem or S3
    2. HttpSensor — poll an HTTP endpoint until it returns 200 / a condition
    3. ExternalTaskSensor — wait for a task in another DAG to complete
    4. S3KeySensor — wait for an S3 key (object) to exist
    5. Poke mode vs. Reschedule mode — critical performance distinction
    6. Sensor timeout and soft_fail behavior
    7. Custom sensor using BaseSensorOperator

BUSINESS USE CASE:
    Cross-team data pipeline coordination:
    - Wait for the finance team to drop today's GL export file on SFTP
    - Wait for the upstream ETL API to expose "READY" status
    - Wait for the upstream data quality DAG to complete successfully
    - Then process the validated data and run downstream ML scoring

SENSOR MODES:
    - poke_mode (default): Sensor occupies a worker slot for its entire wait time
      → Use for short waits (< 5 minutes)
    - reschedule_mode: Sensor releases the worker slot between polls
      → Use for long waits (hours) to avoid starving the worker pool
      → Task state shows as "up_for_reschedule" between polls

POKE INTERVAL vs. TIMEOUT:
    - poke_interval: Seconds between each poll (default: 60s)
    - timeout: Max seconds to wait before failing (default: 7 days!)
    - Always set an explicit timeout to avoid indefinitely blocking sensors

PERFORMANCE NOTES:
    - mode='reschedule' is strongly recommended for sensors with poke_interval > 5 min
    - Set reasonable timeouts — a 7-day default sensor can block a worker for a week
    - For S3 sensors on large buckets, use specific key prefixes not wildcard patterns
    - Consider using dataset-driven scheduling (DAG 07) instead of ExternalTaskSensor
      for Airflow 2.4+ setups

COMMON MISTAKES:
    1. Using mode='poke' for sensors that wait > 1 hour (starves worker pool)
    2. Setting poke_interval < 30s (hammers external systems with requests)
    3. Forgetting to set timeout (sensor runs indefinitely)
    4. Using ExternalTaskSensor without pinning execution_date_fn
       (causes incorrect date matching)
    5. Not handling soft_fail=True correctly — task becomes SKIPPED, not FAILED

INTERVIEW QUESTIONS:
    Q: What is the difference between poke mode and reschedule mode?
    A: Poke mode keeps a worker slot busy during the entire wait (polling in a loop).
       Reschedule mode releases the worker slot between polls and re-queues the sensor
       at each interval. Use reschedule for anything > 5-minute waits.

    Q: When would you use ExternalTaskSensor vs. Datasets?
    A: ExternalTaskSensor: when you need to wait for a specific task in another DAG,
       and you have a fixed schedule relationship. It's fragile if schedules change.
       Datasets (Airflow 2.4+): event-driven, decoupled — a downstream DAG triggers
       automatically when an upstream DAG produces a dataset. Preferred for new setups.

    Q: What happens if a sensor times out?
    A: If soft_fail=False (default): task is marked FAILED, triggering retries and alerts.
       If soft_fail=True: task is marked SKIPPED, and downstream tasks proceed normally.
       Use soft_fail=True for optional data sources.

    Q: How do you make a custom sensor?
    A: Extend BaseSensorOperator and implement the poke() method.
       Return True to stop polling (condition met), False to continue.

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.base import BaseSensorOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.sensors.filesystem import FileSensor
from airflow.sensors.http import HttpSensor
from airflow.utils.context import Context

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DEFAULT ARGS
# ---------------------------------------------------------------------------
default_args: dict = {
    "owner": "data-engineering-diaries",
    "email_on_failure": True,
    "email": ["data-team@company.com"],
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ---------------------------------------------------------------------------
# CUSTOM SENSOR: DatabaseReadinessChecker
# Extends BaseSensorOperator to create a reusable, parameterized sensor
# ---------------------------------------------------------------------------
class DatabaseReadinessChecker(BaseSensorOperator):
    """
    Custom sensor that polls the database metadata table to check if
    an upstream process has marked today's data as "READY".

    This pattern is used when:
    - Source system writes a "ready" flag to a control table
    - You need to wait for a specific business condition (not a file or HTTP call)
    - You want encapsulated, reusable polling logic

    Attributes:
        conn_id (str): Airflow Connection ID for the database
        table_name (str): Control table to query
        expected_status (str): Status value to wait for (default: 'READY')
    """

    # template_fields: Jinja-templatable attributes
    template_fields = ("execution_date_str",)

    def __init__(
        self,
        conn_id: str,
        table_name: str,
        expected_status: str = "READY",
        execution_date_str: str = "{{ ds }}",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.conn_id = conn_id
        self.table_name = table_name
        self.expected_status = expected_status
        self.execution_date_str = execution_date_str

    def poke(self, context: Context) -> bool:
        """
        Poll the control table for the ready status.

        Returns:
            bool: True if condition is met (stop polling), False to continue
        """
        self.log.info(
            "Checking %s for status='%s' on date=%s",
            self.table_name,
            self.expected_status,
            self.execution_date_str,
        )

        # In production: use PostgresHook / SnowflakeHook to run actual query
        # hook = PostgresHook(postgres_conn_id=self.conn_id)
        # result = hook.get_first(
        #     f"SELECT status FROM {self.table_name} WHERE process_date = %s",
        #     parameters=(self.execution_date_str,)
        # )
        # return result is not None and result[0] == self.expected_status

        # Simulated: return True after first poke (in production, this is the DB query)
        self.log.info("Simulated poke: condition MET — returning True")
        return True


# ---------------------------------------------------------------------------
# CALLABLE FUNCTIONS
# ---------------------------------------------------------------------------

def process_arrived_data(**context: dict) -> None:
    """Process data after all sensors have confirmed availability."""
    log.info("All upstream dependencies confirmed. Processing data for %s", context["ds"])
    log.info("Executing downstream ML scoring and aggregation jobs...")
    # In production: trigger Spark job, run dbt models, etc.


def verify_http_response(response: Any) -> bool:
    """
    Custom response check function for HttpSensor.
    Called with the HTTP response object after each poke.

    Returns:
        bool: True if the response indicates readiness (sensor stops polling)
    """
    import json
    try:
        data = response.json()
        status = data.get("status", "UNKNOWN")
        log.info("API status response: %s", status)
        return status == "READY"
    except Exception:
        # If response isn't JSON or parsing fails, check status code
        return response.status_code == 200


# ---------------------------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------------------------
with DAG(
    dag_id="04_sensor_patterns",
    description="Sensors: FileSensor, HttpSensor, ExternalTaskSensor, custom BaseSensorOperator",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 8 * * 1-5",  # Weekdays at 08:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=["sensors", "patterns", "data-engineering-diaries"],
    doc_md="""
## Sensor Patterns DAG

Demonstrates all major Airflow sensor types and modes.

### Sensors Used
| Sensor | Purpose | Mode |
|--------|---------|------|
| FileSensor | Wait for GL export file | reschedule |
| HttpSensor | Wait for API ready status | reschedule |
| ExternalTaskSensor | Wait for upstream ETL DAG | reschedule |
| DatabaseReadinessChecker | Custom control table poller | poke |

### Timing
All sensors use `mode='reschedule'` to avoid blocking worker slots.
    """,
) as dag:

    start = EmptyOperator(task_id="start")

    # -----------------------------------------------------------------------
    # SENSOR 1: FileSensor
    # Waits for a file to appear at a given filesystem path.
    # In production: use S3KeySensor (from airflow.providers.amazon.aws.sensors.s3)
    #               for cloud-based file detection.
    # -----------------------------------------------------------------------
    wait_for_gl_file = FileSensor(
        task_id="wait_for_gl_export_file",

        # The file path to poll — supports Jinja templating
        filepath="/data/incoming/gl_export_{{ ds_nodash }}.csv",

        # Connection ID pointing to the filesystem root
        # For local FS: use 'fs_default'; for SFTP: use SSHSensor instead
        fs_conn_id="fs_default",

        # Mode: 'reschedule' releases worker slot between polls
        # Critical for sensors with poke_interval > 5 minutes
        mode="reschedule",

        # Poll every 5 minutes (300 seconds)
        poke_interval=300,

        # Fail after 8 hours of waiting (SLA for morning file delivery)
        timeout=60 * 60 * 8,

        # soft_fail=True → SKIPPED instead of FAILED on timeout
        # Use when the file is optional
        soft_fail=False,

        doc_md="Wait for the GL export CSV file from the finance team's SFTP drop.",
    )

    # -----------------------------------------------------------------------
    # SENSOR 2: HttpSensor
    # Polls an HTTP endpoint until it returns a condition.
    # Uses 'http_default' connection (set in Admin → Connections).
    # -----------------------------------------------------------------------
    wait_for_api_ready = HttpSensor(
        task_id="wait_for_source_api_ready",

        # Connection ID for the HTTP connection (base URL configured there)
        http_conn_id="http_default",

        # Endpoint to poll (appended to base URL from connection)
        endpoint="api/v1/pipeline/status",

        # HTTP method
        request_params={"date": "{{ ds }}", "pipeline": "gl_extraction"},

        # Custom function to evaluate response — must return bool
        # Default behavior: True if response status code is 200
        response_check=verify_http_response,

        mode="reschedule",
        poke_interval=120,     # Poll every 2 minutes
        timeout=60 * 60 * 4,  # Fail after 4 hours

        doc_md="Poll the ERP API status endpoint until it signals data is READY.",
    )

    # -----------------------------------------------------------------------
    # SENSOR 3: ExternalTaskSensor
    # Waits for a specific task in ANOTHER DAG to reach a target state.
    # Useful for cross-DAG dependencies.
    # -----------------------------------------------------------------------
    wait_for_upstream_etl = ExternalTaskSensor(
        task_id="wait_for_etl_pipeline_completion",

        # The DAG to monitor
        external_dag_id="02_etl_pipeline",

        # The specific task to wait for (None = wait for entire DAG to succeed)
        external_task_id="end",

        # Target state(s) to wait for
        allowed_states=["success"],

        # States that cause this sensor to FAIL immediately (don't wait)
        failed_states=["failed", "upstream_failed"],

        # execution_date_fn: Maps this DAG's execution date to the external DAG's
        # Default: same execution date. Use a lambda to offset:
        # execution_date_fn=lambda dt: dt - timedelta(hours=1)
        execution_date_fn=None,

        mode="reschedule",
        poke_interval=60,
        timeout=60 * 60 * 6,  # 6-hour timeout

        doc_md="Wait for '02_etl_pipeline' to complete successfully before processing.",
    )

    # -----------------------------------------------------------------------
    # SENSOR 4: Custom DatabaseReadinessChecker
    # -----------------------------------------------------------------------
    wait_for_db_ready = DatabaseReadinessChecker(
        task_id="wait_for_db_readiness_flag",
        conn_id="postgres_finance_db",
        table_name="control.pipeline_readiness",
        expected_status="READY",
        mode="poke",            # Short wait — use poke (< 5 min expected)
        poke_interval=30,
        timeout=60 * 60 * 1,   # 1-hour timeout
        doc_md="Poll control.pipeline_readiness until status='READY' for today.",
    )

    # -----------------------------------------------------------------------
    # PROCESSING TASK (runs after all sensors succeed)
    # -----------------------------------------------------------------------
    process_data = PythonOperator(
        task_id="process_arrived_data",
        python_callable=process_arrived_data,
        doc_md="Run downstream processing after all sensors confirm data availability.",
    )

    end = EmptyOperator(task_id="end")

    # -----------------------------------------------------------------------
    # TASK DEPENDENCIES
    # All four sensors run in parallel (fan-out from start)
    # Processing only starts when ALL sensors succeed (fan-in)
    # -----------------------------------------------------------------------
    start >> [wait_for_gl_file, wait_for_api_ready, wait_for_upstream_etl, wait_for_db_ready]
    [wait_for_gl_file, wait_for_api_ready, wait_for_upstream_etl, wait_for_db_ready] >> process_data
    process_data >> end
