"""
Module 06: Databricks Jobs — Orchestrating Multi-Task Workflows via REST & SDK
==============================================================================

Explanation:
    Databricks Jobs is the production orchestration engine for running automated data pipelines,
    machine learning workflows, and analytics tasks. Jobs support multi-task DAGs with complex
    dependencies, conditional branching, retries, and cluster sharing (Job Clusters).

Business Use Case:
    - Orchestrating enterprise end-to-end Medallion pipelines (Ingest -> Transform -> Aggregate -> Publish).
    - Running scheduled nightly batch processing and SLA monitoring.
    - Triggering event-driven pipelines on cloud file arrival or webhook notifications.
    - Provisioning ephemeral job clusters to optimize compute costs (shut down on task completion).

Architecture:
    +-----------------------------------------------------------------------+
    |                         Databricks Job DAG                            |
    |                                                                       |
    |  +--------------------+        +---------------------+                |
    |  | Task 1: Ingestion  | ---->  | Task 2: DLT Silver  |                |
    |  | (Notebook Task)    |        | (Pipeline Task)     |                |
    |  +--------------------+        +---------------------+                |
    |                                           |                           |
    |                                           v                           |
    |                                +---------------------+                |
    |                                | Task 3: SQL Gold    |                |
    |                                | (Databricks SQL)    |                |
    |                                +---------------------+                |
    +-----------------------------------------------------------------------+

Performance Notes:
    - Use Job Clusters instead of All-Purpose Clusters to reduce DBU costs by up to 50%.
    - Reuse job clusters across tasks in the same DAG (task-level cluster sharing) to eliminate spin-up latency.
    - Enable retry policies with exponential backoff for transient network issues.

Common Mistakes:
    - Running production scheduled jobs on interactive (All-Purpose) clusters.
    - Omitting timeout configurations, causing hung tasks to run indefinitely and accumulate costs.
    - Not setting notification alerts for failed or retried tasks.

Interview Questions:
    Q: How do Job Clusters differ from All-Purpose Clusters in Databricks?
    A: Job Clusters are created automatically when a job starts and terminated when it finishes.
       They cost significantly less DBU per hour and guarantee isolated resources for production workloads.

    Q: What is repair run in Databricks Jobs?
    A: When a multi-task job fails mid-stream, repair run allows re-executing ONLY the failed tasks
       and their downstream dependents, avoiding re-running previously successful upstream tasks.
"""

import logging
import time
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabricksJobManager:
    """
    Wrapper for creating, triggering, monitoring, and repairing Databricks Jobs (Workflows).
    Supports simulation mode when running without live Databricks credentials.
    """

    def __init__(self, host: Optional[str] = None, token: Optional[str] = None):
        self.host = host or "https://demo.cloud.databricks.com"
        self.token = token or "dapi_mock_token"
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def build_job_spec(
        self,
        job_name: str,
        tasks: List[Dict[str, Any]],
        cron_schedule: Optional[str] = None,
        job_cluster_key: str = "shared_job_cluster",
        node_type: str = "i3.xlarge",
        num_workers: int = 2,
        email_notifications: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Constructs a standard Databricks Jobs API v2.1 payload for a multi-task DAG.
        """
        job_clusters = [
            {
                "job_cluster_key": job_cluster_key,
                "new_cluster": {
                    "spark_version": "14.3.x-scala2.12",
                    "node_type_id": node_type,
                    "num_workers": num_workers,
                    "spark_conf": {
                        "spark.databricks.delta.preview.enabled": "true",
                        "spark.sql.adaptive.enabled": "true",
                    },
                },
            }
        ]

        spec: Dict[str, Any] = {
            "name": job_name,
            "job_clusters": job_clusters,
            "tasks": tasks,
            "max_concurrent_runs": 1,
            "timeout_seconds": 7200,
        }

        if cron_schedule:
            spec["schedule"] = {
                "quartz_cron_expression": cron_schedule,
                "timezone_id": "UTC",
                "pause_status": "UNPAUSED",
            }

        if email_notifications:
            spec["email_notifications"] = {
                "on_failure": email_notifications,
                "on_success": [],
            }

        logger.info(f"Built Job Payload for '{job_name}' with {len(tasks)} tasks.")
        return spec

    def create_notebook_task(
        self,
        task_key: str,
        notebook_path: str,
        depends_on: Optional[List[str]] = None,
        base_parameters: Optional[Dict[str, str]] = None,
        job_cluster_key: str = "shared_job_cluster",
    ) -> Dict[str, Any]:
        """
        Creates a notebook task specification block for job payload.
        """
        task = {
            "task_key": task_key,
            "job_cluster_key": job_cluster_key,
            "notebook_task": {
                "notebook_path": notebook_path,
                "base_parameters": base_parameters or {},
            },
        }
        if depends_on:
            task["depends_on"] = [{"task_key": dep} for dep in depends_on]
        return task

    def create_sql_task(
        self,
        task_key: str,
        query_id: str,
        warehouse_id: str,
        depends_on: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Databricks SQL task specification block.
        """
        task = {
            "task_key": task_key,
            "sql_task": {
                "query": {"query_id": query_id},
                "warehouse_id": warehouse_id,
            },
        }
        if depends_on:
            task["depends_on"] = [{"task_key": dep} for dep in depends_on]
        return task

    def trigger_job(self, job_id: int, notebook_params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Triggers a job execution (run-now API).
        """
        logger.info(f"Triggering run for job_id={job_id} with params={notebook_params}")
        # Returns simulated run response
        return {
            "run_id": 987654321,
            "job_id": job_id,
            "number_in_job": 42,
            "state": {"life_cycle_state": "PENDING"},
        }

    def poll_job_status(self, run_id: int, max_retries: int = 5, delay_seconds: int = 2) -> Dict[str, Any]:
        """
        Polls run status until completion or timeout.
        """
        logger.info(f"Polling job status for run_id={run_id}...")
        states = ["PENDING", "RUNNING", "TERMINATED"]
        final_result = {
            "run_id": run_id,
            "state": {
                "life_cycle_state": "TERMINATED",
                "result_state": "SUCCESS",
                "state_message": "Run completed successfully.",
            },
        }
        for attempt, state in enumerate(states, start=1):
            logger.info(f"Attempt {attempt}: Run {run_id} state = {state}")
            time.sleep(0.1)  # fast simulation for testing
        return final_result


if __name__ == "__main__":
    job_mgr = DatabricksJobManager()

    # Build 3-task DAG
    t1 = job_mgr.create_notebook_task("ingest_raw", "/Repos/prod/ingestion", base_parameters={"env": "prod"})
    t2 = job_mgr.create_notebook_task("transform_silver", "/Repos/prod/silver", depends_on=["ingest_raw"])
    t3 = job_mgr.create_sql_task("publish_gold", query_id="q_12345", warehouse_id="wh_999", depends_on=["transform_silver"])

    job_payload = job_mgr.build_job_spec(
        job_name="daily_medallion_etl",
        tasks=[t1, t2, t3],
        cron_schedule="0 0 2 * * ?",  # Daily at 2 AM
        email_notifications=["data-eng@example.com"],
    )

    print("=== Complete Job Definition Payload ===")
    import json
    print(json.dumps(job_payload, indent=2))

    run_info = job_mgr.trigger_job(job_id=101)
    status = job_mgr.poll_job_status(run_info["run_id"])
    print("Final Run Status:", status["state"])
