"""
DAG: 07_data_aware_dag.py
=========================

PURPOSE:
    Demonstrates Data-Aware Scheduling (Airflow Datasets) introduced in Airflow 2.4+.
    Datasets decouple DAG schedules from time-based cron intervals, shifting to an
    event-driven architecture where downstream DAGs trigger automatically when
    upstream tasks emit updates to registered Dataset URIs.

CONCEPTS COVERED:
    1. Dataset object: Defining URI pointers (`Dataset("s3://warehouse/sales_fact")`)
    2. Dataset Producers: Tasks specifying `outlets=[dataset]`
    3. Dataset Consumers: DAGs specifying `schedule=[dataset]` or boolean expressions (`schedule=(ds1 & ds2)`)
    4. Dataset Metadata: Attaching extra metadata payload on update
    5. UI Lineage Visualization: Dataset graph in Airflow UI

BUSINESS USE CASE:
    Modern Data Warehouse Refresh:
    - Producer DAG 1: Ingests raw Customer Profile updates from Postgres into S3
    - Producer DAG 2: Ingests raw Orders & Line Items from Kafka into S3
    - Consumer DAG (Customer 360): Triggers AUTOMATICALLY only when BOTH Customer
      and Order datasets are updated for the day. Runs dbt model transforms.

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

from airflow import DAG
from airflow.datasets import Dataset
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DATASET DEFINITIONS
# URIs must strictly follow URI standard (e.g. s3://bucket/key, postgres://host/db/table)
# Datasets are normalized standard strings used by Airflow's dependency engine.
# ---------------------------------------------------------------------------
RAW_CUSTOMERS_DATASET = Dataset("s3://analytics-lakehouse-prod/raw/customers/partition_date={{ ds }}")
RAW_ORDERS_DATASET = Dataset("s3://analytics-lakehouse-prod/raw/orders/partition_date={{ ds }}")
CUST_360_MART_DATASET = Dataset("postgres://dw-prod.internal:5432/analytics/marts/customer_360")

default_args = {
    "owner": "data-engineering-diaries",
    "email_on_failure": True,
    "email": ["warehouse-team@company.com"],
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ===========================================================================
# PRODUCER DAG 1: Customer Profile Ingestion
# Scheduled daily via Cron, updates RAW_CUSTOMERS_DATASET on completion
# ===========================================================================
with DAG(
    dag_id="07_producer_customer_ingestion",
    description="Producer DAG 1: Ingests daily customer master data updates",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",  # 02:00 UTC daily
    catchup=False,
    tags=["dataset-producer", "customers", "ingestion", "data-engineering-diaries"],
) as producer_customers_dag:

    start_c = EmptyOperator(task_id="start")

    def ingest_customer_master(**context):
        log.info("Extracting customer updates from CRM DB...")
        row_count = random.randint(100, 2500)
        log.info("Successfully wrote %d customer records to S3 staging.", row_count)
        return {"records_ingested": row_count}

    # outlets parameter defines which Datasets this task updates upon SUCCESS
    ingest_customers = PythonOperator(
        task_id="ingest_customer_data",
        python_callable=ingest_customer_master,
        outlets=[RAW_CUSTOMERS_DATASET],
        doc_md="Ingests CRM updates and registers update event for RAW_CUSTOMERS_DATASET.",
    )

    end_c = EmptyOperator(task_id="end")

    start_c >> ingest_customers >> end_c


# ===========================================================================
# PRODUCER DAG 2: Order Transactions Ingestion
# Scheduled daily via Cron, updates RAW_ORDERS_DATASET on completion
# ===========================================================================
with DAG(
    dag_id="07_producer_orders_ingestion",
    description="Producer DAG 2: Ingests daily order transaction batch",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 3 * * *",  # 03:00 UTC daily
    catchup=False,
    tags=["dataset-producer", "orders", "ingestion", "data-engineering-diaries"],
) as producer_orders_dag:

    start_o = EmptyOperator(task_id="start")

    def ingest_order_batch(**context):
        log.info("Extracting transactions from POS Kafka topics...")
        order_count = random.randint(10000, 50000)
        log.info("Successfully staged %d transaction records to S3.", order_count)
        return {"orders_staged": order_count}

    ingest_orders = PythonOperator(
        task_id="ingest_order_transactions",
        python_callable=ingest_order_batch,
        outlets=[RAW_ORDERS_DATASET],
        doc_md="Ingests order batch and registers update event for RAW_ORDERS_DATASET.",
    )

    end_o = EmptyOperator(task_id="end")

    start_o >> ingest_orders >> end_o


# ===========================================================================
# CONSUMER DAG: Customer 360 Analytics Datamart
# Scheduled via Dataset dependency: Triggers AUTOMATICALLY when BOTH datasets update!
# Airflow 2.4+ dataset logical expressions: schedule=(ds1 & ds2)
# ===========================================================================
with DAG(
    dag_id="07_consumer_customer_360_analytics",
    description="Consumer DAG: Triggered event-driven when both Customer & Order datasets update",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    # Boolean logic: wait for BOTH upstream dataset update events
    schedule=(RAW_CUSTOMERS_DATASET & RAW_ORDERS_DATASET),
    catchup=False,
    tags=["dataset-consumer", "event-driven", "datamart", "data-engineering-diaries"],
    doc_md="""
## Data-Aware Consumer DAG: Customer 360

This DAG has NO time-based schedule (no cron string).
Instead, it is triggered by Airflow's Dataset event engine whenever **BOTH**:
1. `RAW_CUSTOMERS_DATASET` has been updated by `07_producer_customer_ingestion`
2. `RAW_ORDERS_DATASET` has been updated by `07_producer_orders_ingestion`
    """,
) as consumer_c360_dag:

    start_consumer = EmptyOperator(task_id="start_event_driven_pipeline")

    def run_dbt_customer_360(**context):
        """Simulate dbt transformation compiling customer 360 feature store."""
        log.info("Reading updated inputs from S3 lakehouse...")
        log.info("Executing dbt run --select dim_customers fct_orders customer_360_mart...")
        log.info("dbt models built successfully in Data Warehouse.")

    build_c360_mart = PythonOperator(
        task_id="build_customer_360_mart",
        python_callable=run_dbt_customer_360,
        # Emits downstream dataset update event for consumer systems/dashboards
        outlets=[CUST_360_MART_DATASET],
        doc_md="Runs dbt transformations and emits update for CUST_360_MART_DATASET.",
    )

    notify_bi_dashboards = BashOperator(
        task_id="notify_bi_dashboards",
        bash_command="echo 'BI Dashboards cache invalidated and re-warmed at {{ ts }}'",
        doc_md="Invalidates Tableau / PowerBI cache.",
    )

    end_consumer = EmptyOperator(task_id="end_event_driven_pipeline")

    start_consumer >> build_c360_mart >> notify_bi_dashboards >> end_consumer
