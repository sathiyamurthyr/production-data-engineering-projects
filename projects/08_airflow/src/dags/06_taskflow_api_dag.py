"""
DAG: 06_taskflow_api_dag.py
===========================

PURPOSE:
    Demonstrates modern Airflow TaskFlow API (@dag, @task, @task.branch, @task.group)
    introduced in Airflow 2.0+, including Dynamic Task Mapping (.expand(), .partial())
    introduced in Airflow 2.3+.

CONCEPTS COVERED:
    1. @dag decorator: Clean DAG definition without context manager boilerplate
    2. @task decorator: Python callable as a task with auto XCom push/pull
    3. Type hints in TaskFlow: Automatic serialization/deserialization
    4. @task.branch decorator: Clean conditional branching logic
    5. @task.group decorator: Grouping tasks inside TaskFlow functions
    6. Dynamic Task Mapping (.expand()): Spawning dynamic task instances at runtime
    7. Combining TaskFlow tasks with traditional Operators

BUSINESS USE CASE:
    E-Commerce Multi-Region Revenue Aggregation:
    - Extract active sales regions dynamically from config
    - Map extraction task dynamically across all regions (parallel tasks per region)
    - Transform region datasets, apply regional currency conversion and tax rates
    - Branch: check if overall total revenue meets daily target
    - Target met -> promote to executive summary datamart
    - Target missed -> route to anomaly investigation task

DAG FLOW:
    get_active_regions
        └─► extract_region_data.expand() [Dynamic Mapping across regions]
                └─► transform_region_data.expand()
                        └─► aggregate_global_revenue
                                └─► check_target_branch
                                        ├── [Target Met]  ──► publish_executive_summary
                                        └── [Target Miss] ──► log_target_miss_anomaly

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from airflow.decorators import dag, task, task_group
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)

# Default arguments applied to all tasks inside the @dag
default_args = {
    "owner": "data-engineering-diaries",
    "email_on_failure": True,
    "email": ["analytics-team@company.com"],
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}


@dag(
    dag_id="06_taskflow_api_pipeline",
    description="Modern TaskFlow API workflow with Dynamic Task Mapping (.expand()) and @task.branch",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 4 * * *",  # Daily at 04:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=["taskflow", "dynamic-mapping", "analytics", "data-engineering-diaries"],
    doc_md="""
## TaskFlow API & Dynamic Mapping Pipeline

Demonstrates modern Airflow 2.x paradigms:
- `@dag` decorator replaces explicit `with DAG(...)`
- `@task` decorates Python functions, handling XCom implicitly via return values and arguments
- `.expand()` dynamically creates task instances based on runtime list length
- `@task.branch` routes execution based on calculated metrics
    """,
)
def taskflow_api_pipeline():

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    @task(doc_md="Fetch active sales region configurations.")
    def get_active_regions() -> List[Dict[str, Any]]:
        """
        Extract active region parameters.
        In production, this would query a database or API endpoint.
        """
        regions = [
            {"region_id": "NA_EAST", "currency": "USD", "tax_rate": 0.07},
            {"region_id": "NA_WEST", "currency": "USD", "tax_rate": 0.08},
            {"region_id": "EU_CENTRAL", "currency": "EUR", "tax_rate": 0.19},
            {"region_id": "APAC_SOUTH", "currency": "SGD", "tax_rate": 0.09},
            {"region_id": "LATAM_BRAZIL", "currency": "BRL", "tax_rate": 0.12},
        ]
        log.info("Discovered %d active sales regions for processing", len(regions))
        return regions

    @task(doc_md="Extract raw transaction data for a single region.")
    def extract_region_data(region_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically mapped task instance per region.
        """
        region_id = region_info["region_id"]
        log.info("Extracting raw transactions for region: %s", region_id)

        # Simulated raw extraction metric
        raw_count = random.randint(5000, 25000)
        gross_sales = round(random.uniform(50000.0, 250000.0), 2)

        return {
            "region_id": region_id,
            "currency": region_info["currency"],
            "tax_rate": region_info["tax_rate"],
            "raw_count": raw_count,
            "gross_sales": gross_sales,
        }

    @task(doc_md="Transform region data: apply tax calculations and currency conversion.")
    def transform_region_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw regional payload into standardized USD revenue metrics.
        """
        region_id = raw_data["region_id"]
        gross_sales = raw_data["gross_sales"]
        tax_rate = raw_data["tax_rate"]
        currency = raw_data["currency"]

        # Exchange rate lookup (mocked)
        fx_rates = {"USD": 1.0, "EUR": 1.08, "SGD": 0.74, "BRL": 0.20}
        fx_rate = fx_rates.get(currency, 1.0)

        tax_amount = gross_sales * tax_rate
        net_sales_local = gross_sales - tax_amount
        net_sales_usd = round(net_sales_local * fx_rate, 2)

        log.info(
            "[%s] Gross: %.2f %s | Tax: %.2f | Net USD: %.2f (FX: %.2f)",
            region_id, gross_sales, currency, tax_amount, net_sales_usd, fx_rate,
        )

        return {
            "region_id": region_id,
            "net_sales_usd": net_sales_usd,
            "transaction_count": raw_data["raw_count"],
        }

    @task(doc_md="Aggregate overall net revenue across all mapped regional outputs.")
    def aggregate_global_revenue(regional_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolidates list of transformed region dicts into global totals.
        """
        total_usd = sum(m["net_sales_usd"] for m in regional_metrics)
        total_tx = sum(m["transaction_count"] for m in regional_metrics)
        region_count = len(regional_metrics)

        log.info("Global Revenue Aggregation Complete:")
        log.info("  Total Regions: %d", region_count)
        log.info("  Total Transactions: %d", total_tx)
        log.info("  Total Net Revenue (USD): $%.2f", total_usd)

        return {
            "total_net_revenue_usd": total_usd,
            "total_transactions": total_tx,
            "region_count": region_count,
        }

    @task.branch(doc_md="Branch on calculated revenue target ($500,000 threshold).")
    def check_revenue_target(global_summary: Dict[str, Any]) -> str:
        """
        TaskFlow branch decorator evaluating revenue threshold.
        """
        target_threshold = 500000.0
        actual_revenue = global_summary["total_net_revenue_usd"]

        if actual_revenue >= target_threshold:
            log.info("Revenue target MET ($%.2f >= $%.2f). Branching to publish.", actual_revenue, target_threshold)
            return "publish_executive_summary"
        else:
            log.warning("Revenue target MISSED ($%.2f < $%.2f). Branching to anomaly log.", actual_revenue, target_threshold)
            return "log_target_miss_anomaly"

    @task(doc_md="Publish final summary to Executive BI Data Mart.")
    def publish_executive_summary(global_summary: Dict[str, Any]) -> None:
        """
        Loads aggregated metrics into production datamart table.
        """
        log.info("Writing metrics to DW datamart: %s", global_summary)

    @task(doc_md="Log target miss event to ops dashboard.")
    def log_target_miss_anomaly(global_summary: Dict[str, Any]) -> None:
        """
        Records revenue deficiency for financial ops review.
        """
        log.warning("Recording anomaly for underperforming revenue: %s", global_summary)

    # -----------------------------------------------------------------------
    # DAG Pipeline Execution / Dependency Graph Construction
    # -----------------------------------------------------------------------
    active_regions = get_active_regions()

    # Dynamic task mapping (.expand) creates an extract instance per region
    raw_regional_payloads = extract_region_data.expand(region_info=active_regions)

    # Dynamic task mapping (.expand) transforms each regional payload in parallel
    transformed_regional_payloads = transform_region_data.expand(raw_data=raw_regional_payloads)

    # Aggregates mapped results back into a single dictionary
    global_metrics = aggregate_global_revenue(regional_metrics=transformed_regional_payloads)

    # Branch condition
    branch_choice = check_revenue_target(global_summary=global_metrics)

    pub_task = publish_executive_summary(global_summary=global_metrics)
    anomaly_task = log_target_miss_anomaly(global_summary=global_metrics)

    # Set up graph dependencies with sentinels
    start >> active_regions
    branch_choice >> [pub_task, anomaly_task]
    [pub_task, anomaly_task] >> end


# Instantiate the DAG
dag_instance = taskflow_api_pipeline()
