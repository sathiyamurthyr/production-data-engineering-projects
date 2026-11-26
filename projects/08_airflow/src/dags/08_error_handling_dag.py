"""
DAG: 08_error_handling_dag.py
============================

PURPOSE:
    Demonstrates production-grade resilience, fault tolerance, and alert handling in Airflow.
    Teaches retries with exponential backoff, SLA tracking, task lifecycle callbacks,
    Dead Letter Queue (DLQ) exception routing, and custom exception classes.

CONCEPTS COVERED:
    1. Retries & Exponential Backoff: Preventing API rate limits and transient worker failures
    2. Task & DAG Callbacks: `on_failure_callback`, `on_retry_callback`, `on_success_callback`
    3. SLA (Service Level Agreement) Monitoring & `sla_miss_callback`
    4. Trigger Rules for Fallback Execution (`TriggerRule.ONE_FAILED`, `TriggerRule.ALL_FAILED`)
    5. Dead Letter Queue (DLQ) pattern: Isolating bad records/failed runs for manual audit
    6. `AirflowException` vs `AirflowSkipException` vs `AirflowFailException`

BUSINESS USE CASE:
    Mission-Critical Payment Settlement Pipeline:
    - Must complete within 45-minute SLA window for banking cutoff
    - Primary Payment API call has transient network retries with exponential backoff
    - If payment processing task fails after all retries, pipeline routes to DLQ handler
    - Dead Letter Queue logs failing transaction payload details to database table
    - Triggers PagerDuty / Slack alerts with full execution context, stack trace, and log URLs

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict

from airflow import DAG
from airflow.exceptions import AirflowException, AirflowFailException, AirflowSkipException
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LIFECYCLE CALLBACK FUNCTIONS
# ---------------------------------------------------------------------------
def task_failure_alert(context: Dict[str, Any]) -> None:
    """
    Executed automatically whenever ANY task in the DAG reaches FAILED state.
    """
    ti = context.get("task_instance")
    exception = context.get("exception")
    execution_date = context.get("ds")
    log_url = ti.log_url if ti else "N/A"

    alert_message = (
        f"🚨 [CRITICAL TASK FAILURE]\n"
        f"DAG: {ti.dag_id if ti else 'unknown'}\n"
        f"Task: {ti.task_id if ti else 'unknown'}\n"
        f"Execution Date: {execution_date}\n"
        f"Try Count: {ti.try_number if ti else 1}\n"
        f"Error Details: {exception}\n"
        f"Logs: {log_url}"
    )
    log.error(alert_message)
    # In production: send to Slack Webhook or PagerDuty API


def task_retry_alert(context: Dict[str, Any]) -> None:
    """
    Executed automatically when a task fails but has retries remaining.
    """
    ti = context.get("task_instance")
    log.warning(
        "⚠️ [TASK RETRY ALERT] Task '%s' failed attempt #%d. Retrying in background...",
        ti.task_id if ti else "unknown",
        ti.try_number if ti else 1,
    )


def sla_miss_alert(dag, task_list, blocking_task_list, slas, blocking_tis) -> None:
    """
    Triggered by Airflow Scheduler when a task exceeds its defined SLA deadline.
    """
    log.error(
        "⏱️ [SLA MISS ALERT] SLA deadline violated for DAG '%s'!\n"
        "Tasks exceeding SLA: %s\n"
        "Blocking tasks: %s",
        dag.dag_id,
        task_list,
        blocking_task_list,
    )


# Default task arguments with production backoff policy
default_args = {
    "owner": "data-engineering-diaries",
    "email_on_failure": True,
    "email": ["payments-ops@company.com"],
    # Retry policy setup
    "retries": 3,
    "retry_delay": timedelta(seconds=10),
    "retry_exponential_backoff": True,  # Wait increases: 10s -> 20s -> 40s
    "max_retry_delay": timedelta(minutes=5),
    "on_failure_callback": task_failure_alert,
    "on_retry_callback": task_retry_alert,
    "execution_timeout": timedelta(minutes=15),
}


# ---------------------------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------------------------
with DAG(
    dag_id="08_error_handling_resilience",
    description="Resilience patterns: Retries, Exponential Backoff, SLAs, Callbacks, and DLQ",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 1 * * *",  # 01:00 UTC daily
    catchup=False,
    max_active_runs=1,
    sla_miss_callback=sla_miss_alert,
    tags=["error-handling", "resilience", "dlq", "callbacks", "data-engineering-diaries"],
    doc_md="""
## Error Handling & Resilience DAG

Demonstrates enterprise fault tolerance patterns:
- Exponential backoff retries on transient external dependencies
- Callback hooks (`on_failure_callback`, `on_retry_callback`, `sla_miss_callback`)
- Exception handling differentiation (`AirflowSkipException` vs `AirflowFailException`)
- Fallback Dead Letter Queue (DLQ) task with `TriggerRule.ONE_FAILED`
    """,
) as dag:

    start = EmptyOperator(task_id="start")

    # -----------------------------------------------------------------------
    # TASK 1: Pre-flight Validation (Demonstrates AirflowSkipException)
    # -----------------------------------------------------------------------
    def validate_banking_gateway(**context) -> None:
        """
        Validates banking holiday calendar.
        If today is a bank holiday, skip execution cleanly without failing.
        """
        execution_date = context["ds"]
        log.info("Checking holiday calendar for date: %s", execution_date)

        # Simulated holiday check logic
        is_bank_holiday = False  # Set to True to test skip behavior

        if is_bank_holiday:
            log.info("Date %s is a recognized bank holiday. Skipping settlement pipeline.", execution_date)
            raise AirflowSkipException("Bank holiday detected — skipping run.")

        log.info("Banking gateway active. Proceeding with settlement.")

    preflight_check = PythonOperator(
        task_id="preflight_bank_check",
        python_callable=validate_banking_gateway,
        doc_md="Validates operational window. Raises AirflowSkipException on holidays.",
    )

    # -----------------------------------------------------------------------
    # TASK 2: Unreliable Third-Party Payment Gateway Call
    # -----------------------------------------------------------------------
    def process_payment_settlement(**context) -> Dict[str, Any]:
        """
        Simulates calling an external payment gateway API.
        Demonstrates retry logic on transient errors.
        """
        ti = context["ti"]
        attempt = ti.try_number

        log.info("Attempting payment settlement API call (Attempt #%d)...", attempt)

        # Simulate 60% chance of transient failure on first two attempts
        failure_roll = random.random()

        if attempt < 3 and failure_roll < 0.6:
            log.warning("Transient network timeout connecting to Payment API gateway.")
            raise AirflowException("Payment Gateway Timeout (HTTP 504) — retryable exception.")

        log.info("Payment settlement API call SUCCEEDED on attempt #%d.", attempt)
        return {
            "status": "SETTLED",
            "batch_id": f"SETTLE_{context['ds_nodash']}_99",
            "records_processed": 4500,
            "total_amount_usd": 1250000.00,
        }

    payment_settlement = PythonOperator(
        task_id="process_payment_settlement",
        python_callable=process_payment_settlement,
        # SLA definition: must finish within 30 minutes of DAG start time
        sla=timedelta(minutes=30),
        doc_md="Process payment batch. Retries with exponential backoff on transient errors.",
    )

    # -----------------------------------------------------------------------
    # TASK 3: Happy Path — Reconcile & Archive
    # -----------------------------------------------------------------------
    def reconcile_settlement(**context) -> None:
        settlement_info = context["ti"].xcom_pull(
            task_ids="process_payment_settlement",
            key="return_value",
        )
        if not settlement_info:
            raise AirflowFailException("No settlement payload found in XCom.")

        log.info("Reconciling settlement batch: %s", settlement_info["batch_id"])
        log.info("Total Settled Amount: $%.2f", settlement_info["total_amount_usd"])

    reconcile_task = PythonOperator(
        task_id="reconcile_settlement",
        python_callable=reconcile_settlement,
        doc_md="Reconcile settled payment batch with internal general ledger.",
    )

    # -----------------------------------------------------------------------
    # TASK 4: Fallback Dead Letter Queue (DLQ) Handler
    # Runs ONLY if upstream payment processing fails completely after all retries.
    # TriggerRule.ONE_FAILED ensures this task runs on failure.
    # -----------------------------------------------------------------------
    def handle_dead_letter_queue(**context) -> None:
        """
        Isolates failed payload and records incident details in audit DLQ table.
        """
        log.error("Executing Dead Letter Queue (DLQ) mitigation pattern...")
        execution_date = context["ds"]
        dag_id = context["dag"].dag_id

        dlq_record = {
            "dag_id": dag_id,
            "execution_date": execution_date,
            "failure_reason": "Payment API Exhausted All Retries",
            "isolation_timestamp": datetime.utcnow().isoformat(),
        }

        log.error("Wrote payload to DW table `audit.dead_letter_queue`: %s", dlq_record)
        log.error("Triggered PagerDuty Critical Alarm for On-Call Engineer.")

    dlq_handler = PythonOperator(
        task_id="dead_letter_queue_handler",
        python_callable=handle_dead_letter_queue,
        trigger_rule=TriggerRule.ONE_FAILED,
        doc_md="DLQ handler triggered when payment settlement task fails.",
    )

    # -----------------------------------------------------------------------
    # End sentinels with proper trigger rules
    # -----------------------------------------------------------------------
    end_success = EmptyOperator(
        task_id="end_success",
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    end_failure = EmptyOperator(
        task_id="end_failure_handled",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # -----------------------------------------------------------------------
    # Graph Dependencies
    # -----------------------------------------------------------------------
    start >> preflight_check >> payment_settlement

    # Success Flow
    payment_settlement >> reconcile_task >> end_success

    # Error / DLQ Flow
    payment_settlement >> dlq_handler >> end_failure
