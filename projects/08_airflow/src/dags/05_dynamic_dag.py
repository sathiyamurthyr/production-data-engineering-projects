"""
DAG: 05_dynamic_dag.py
======================

PURPOSE:
    Demonstrates how to dynamically generate multiple DAGs from a configuration
    source (JSON, YAML, database table, or Airflow Variables). This pattern is
    used in enterprise environments where hundreds of similar pipelines share
    the same code structure but differ in configuration.

CONCEPTS COVERED:
    1. DAG Factory pattern — one Python module creates N DAG objects
    2. globals() pattern — the standard way to register dynamic DAGs
    3. Reading config from Airflow Variables (JSON)
    4. Jinja templating in dynamic DAGs
    5. Avoiding duplicate dag_id errors
    6. Best practices for dynamic DAG generation at scale

BUSINESS USE CASE:
    Multi-tenant SaaS data platform: 50+ customers each need their own daily
    data sync pipeline. Each customer has different:
      - Source database (schema name)
      - Target table prefix
      - Schedule time (staggered to avoid DB contention)
      - Email alert recipients
      - Retry policy

    Instead of 50 separate DAG files, one dynamic generator creates all 50 DAGs
    from a customer configuration dictionary/JSON.

DYNAMIC DAG PATTERN:
    Config → loop → create DAG object → register in globals() → Airflow picks it up

PERFORMANCE NOTES:
    - The DAG file is parsed by the scheduler on every DagFileProcessor cycle
    - Dynamic DAG generation adds parsing overhead proportional to number of DAGs
    - Keep the config source fast: prefer in-file dict or Airflow Variable over DB queries
    - Never make HTTP calls or DB queries at module level in DAG files (slows parsing)
    - Use DagFileProcessorAgent timeout to avoid parsing hangs

COMMON MISTAKES:
    1. Querying databases at module parse time (happens on every scheduler cycle)
    2. Not providing unique dag_ids for each generated DAG
    3. Creating DAGs with mutable closure variables (Python closure bug)
    4. Forgetting to register the DAG object in globals()
    5. Generating too many DAGs (> 1000) — use DAG groups or custom operators instead

INTERVIEW QUESTIONS:
    Q: How do you generate DAGs dynamically in Airflow?
    A: Use a DAG factory function that loops over a configuration list/dict,
       creates DAG objects, and registers them in the module's globals() dict.
       The scheduler discovers all DAG objects at module level on each parse cycle.

    Q: What is the globals() pattern for dynamic DAGs?
    A: globals()[dag_id] = dag registers each generated DAG object as a module-level
       variable, making it discoverable by the Airflow scheduler.

    Q: What are the risks of dynamic DAG generation?
    A: 1. Slow scheduler parsing if config is fetched from external systems
       2. Duplicate dag_id errors if the generation logic isn't deterministic
       3. Hard to debug individual DAGs when logic is shared
       Mitigate with: fast config sources, unique IDs, thorough testing

    Q: When should you use dynamic DAGs vs. parameterized DAG runs?
    A: Dynamic DAGs: when each customer/entity needs its OWN schedule, retry policy,
       and independent monitoring.
       Parameterized runs (DAG w/ config param): when one DAG runs with different
       parameters per run, on a single schedule.

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CUSTOMER CONFIGURATION
# In production, load this from:
#   - Airflow Variable (JSON string): Variable.get("customer_pipeline_config")
#   - A YAML/JSON file in the same directory
#   - A database table (cached, NOT queried at parse time)
#
# IMPORTANT: Do NOT make DB or HTTP calls at module level — they run on every
# scheduler parse cycle (potentially every 30 seconds).
# ---------------------------------------------------------------------------

CUSTOMER_CONFIG: list[dict[str, Any]] = [
    {
        "customer_id": "cust_001",
        "customer_name": "Acme Corp",
        "source_schema": "acme_source",
        "target_prefix": "acme_prod",
        "schedule": "0 1 * * *",       # 01:00 UTC daily
        "retries": 3,
        "retry_delay_minutes": 15,
        "alert_emails": ["acme-data@acme.com", "platform-alerts@company.com"],
        "batch_size": 10000,
        "enabled": True,
    },
    {
        "customer_id": "cust_002",
        "customer_name": "Globex Industries",
        "source_schema": "globex_source",
        "target_prefix": "globex_prod",
        "schedule": "0 2 * * *",       # 02:00 UTC daily (staggered by 1 hour)
        "retries": 2,
        "retry_delay_minutes": 10,
        "alert_emails": ["data@globex.com"],
        "batch_size": 50000,
        "enabled": True,
    },
    {
        "customer_id": "cust_003",
        "customer_name": "Initech LLC",
        "source_schema": "initech_source",
        "target_prefix": "initech_prod",
        "schedule": "0 3 * * 1-5",    # 03:00 UTC weekdays only
        "retries": 1,
        "retry_delay_minutes": 30,
        "alert_emails": ["it-data@initech.com"],
        "batch_size": 5000,
        "enabled": True,
    },
    {
        "customer_id": "cust_004",
        "customer_name": "Umbrella Corp",
        "source_schema": "umbrella_source",
        "target_prefix": "umbrella_prod",
        "schedule": "0 4 * * *",
        "retries": 2,
        "retry_delay_minutes": 20,
        "alert_emails": ["data-team@umbrella.com"],
        "batch_size": 25000,
        "enabled": False,    # Disabled — DAG will be skipped
    },
]


# ---------------------------------------------------------------------------
# DAG FACTORY FUNCTIONS
# Encapsulate all task-creation logic in functions to avoid closure bugs.
# IMPORTANT: Python closures capture variables by reference, not value.
# Always pass config explicitly as function parameters, not via closure.
# ---------------------------------------------------------------------------

def make_extract_callable(config: dict[str, Any]) -> Any:
    """
    Factory: Create a bound Python callable for the extract task.
    Captures config explicitly to avoid closure variable capture bugs.
    """
    def extract(**context: dict) -> dict:
        customer_id = config["customer_id"]
        source_schema = config["source_schema"]
        execution_date = context["ds"]
        batch_size = config["batch_size"]

        log.info(
            "[%s] Extracting from schema '%s' for %s (batch_size=%d)",
            customer_id, source_schema, execution_date, batch_size,
        )

        # In production: use a hook to query source DB
        # hook = PostgresHook(postgres_conn_id=f"src_{customer_id}")
        # records = hook.get_records(
        #     f"SELECT * FROM {source_schema}.transactions WHERE date = %s LIMIT %s",
        #     parameters=(execution_date, batch_size)
        # )

        extracted_rows = 1000  # Simulated
        result = {
            "customer_id": customer_id,
            "source_schema": source_schema,
            "extracted_rows": extracted_rows,
            "execution_date": execution_date,
        }
        log.info("[%s] Extracted %d rows.", customer_id, extracted_rows)
        return result

    return extract


def make_transform_callable(config: dict[str, Any]) -> Any:
    """Factory: Create a bound Python callable for the transform task."""
    def transform(**context: dict) -> dict:
        customer_id = config["customer_id"]
        extract_result: dict = context["ti"].xcom_pull(
            task_ids="extract_data", key="return_value"
        )
        log.info("[%s] Transforming %d rows...", customer_id, extract_result["extracted_rows"])

        transformed_rows = int(extract_result["extracted_rows"] * 0.99)
        return {**extract_result, "transformed_rows": transformed_rows}

    return transform


def make_load_callable(config: dict[str, Any]) -> Any:
    """Factory: Create a bound Python callable for the load task."""
    def load(**context: dict) -> None:
        customer_id = config["customer_id"]
        target_prefix = config["target_prefix"]
        transform_result: dict = context["ti"].xcom_pull(
            task_ids="transform_data", key="return_value"
        )
        log.info(
            "[%s] Loading %d rows into '%s.transactions'...",
            customer_id, transform_result["transformed_rows"], target_prefix,
        )
        log.info(
            "INSERT INTO %s.transactions SELECT ... (%d rows)",
            target_prefix, transform_result["transformed_rows"],
        )

    return load


def create_customer_dag(config: dict[str, Any]) -> DAG:
    """
    DAG Factory: Create a complete DAG for a single customer from config.

    This function is called once per customer during module parsing.
    Each call returns a new DAG object with unique dag_id and configuration.

    Args:
        config: Customer configuration dictionary

    Returns:
        DAG: Configured Airflow DAG object
    """
    customer_id: str = config["customer_id"]
    customer_name: str = config["customer_name"]

    # Each customer gets a unique dag_id — critical to avoid Airflow conflicts
    dag_id: str = f"customer_sync_{customer_id}"

    customer_default_args: dict = {
        "owner": "data-platform-team",
        "email_on_failure": True,
        "email": config["alert_emails"],
        "retries": config["retries"],
        "retry_delay": timedelta(minutes=config["retry_delay_minutes"]),
    }

    with DAG(
        dag_id=dag_id,
        description=f"Daily data sync pipeline for customer: {customer_name}",
        default_args=customer_default_args,
        start_date=datetime(2024, 1, 1),
        schedule=config["schedule"],
        catchup=False,
        max_active_runs=1,
        tags=["dynamic", "customer-sync", customer_id, "data-engineering-diaries"],
        doc_md=f"""
## Customer Sync Pipeline: {customer_name}

**Customer ID**: {customer_id}  
**Source Schema**: {config['source_schema']}  
**Target Prefix**: {config['target_prefix']}  
**Batch Size**: {config['batch_size']:,}  
**Schedule**: {config['schedule']}

This DAG is auto-generated by the dynamic DAG factory in `05_dynamic_dag.py`.
        """,
    ) as customer_dag:

        dag_start = EmptyOperator(task_id="start")

        extract_task = PythonOperator(
            task_id="extract_data",
            python_callable=make_extract_callable(config),
            doc_md=f"Extract data from {config['source_schema']} for {customer_name}.",
        )

        transform_task = PythonOperator(
            task_id="transform_data",
            python_callable=make_transform_callable(config),
            doc_md=f"Clean and normalize {customer_name} data.",
        )

        load_task = PythonOperator(
            task_id="load_data",
            python_callable=make_load_callable(config),
            doc_md=f"Load into {config['target_prefix']}.transactions.",
        )

        dag_end = EmptyOperator(task_id="end")

        dag_start >> extract_task >> transform_task >> load_task >> dag_end

    return customer_dag


# ---------------------------------------------------------------------------
# DYNAMIC DAG REGISTRATION
# Loop over customer configs, create each DAG, register in globals().
# The Airflow scheduler discovers DAG objects at module level.
#
# IMPORTANT: Only register ENABLED customers.
# ---------------------------------------------------------------------------

for _customer_config in CUSTOMER_CONFIG:
    if not _customer_config.get("enabled", True):
        log.info(
            "Skipping disabled customer: %s (%s)",
            _customer_config["customer_name"],
            _customer_config["customer_id"],
        )
        continue

    _dag_id = f"customer_sync_{_customer_config['customer_id']}"
    _dag_object = create_customer_dag(_customer_config)

    # Register in module globals so the scheduler can discover the DAG
    # This is equivalent to defining: customer_sync_cust_001 = DAG(...)
    globals()[_dag_id] = _dag_object
    log.info("Registered dynamic DAG: %s", _dag_id)


# ---------------------------------------------------------------------------
# EXAMPLE: Loading config from Airflow Variables at parse time (safe pattern)
# Use Variable.get with a default — if Variable doesn't exist, falls back gracefully.
# Never raise an exception at parse time — it will break ALL DAGs in the file.
# ---------------------------------------------------------------------------
# _variable_config_raw = Variable.get(
#     "dynamic_dag_config",
#     default_var=json.dumps(CUSTOMER_CONFIG)
# )
# _variable_config = json.loads(_variable_config_raw)
# for cfg in _variable_config:
#     if cfg.get("enabled"):
#         _dag = create_customer_dag(cfg)
#         globals()[_dag.dag_id] = _dag
