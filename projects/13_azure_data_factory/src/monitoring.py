"""
monitoring.py - Azure Data Factory Pipeline Monitoring & Log Analytics Integration
===================================================================================
Production-grade monitoring, run status tracking, SLA validation, and Log Analytics integration.

Explanation:
    Enterprise data pipelines require operational observability. This module provides:
    1. Pipeline Run Status Polling: Synchronously or asynchronously waiting for pipeline completion.
    2. Activity Run Diagnostics: Extracting execution metrics, durations, error tracebacks per activity step.
    3. Log Analytics KQL Queries: Generating Log Analytics Kusto Query Language (KQL) queries for ADF logs.
    4. Alerting & SLA Tracking: Detecting SLA breaches, job failures, and formatting alert payloads.

Business Use Case:
    Production orchestration tools must monitor ADF pipeline execution state, alert on failure,
    log metrics to Azure Log Analytics or Datadog/CloudWatch, and calculate SLA compliance metrics.

Production Example:
    monitor = PipelineMonitor(adf_client)
    status = monitor.wait_for_completion(resource_group="my-rg", factory_name="my-adf", run_id="123-456", timeout_seconds=300)
    if status["status"] == "Failed":
        activities = monitor.get_failed_activity_runs("my-rg", "my-adf", "123-456")
        print("Failed activities:", activities)

Interview Questions:
    Q: Where are ADF pipeline run logs stored and how do you query them?
    A: ADF sends Diagnostic Logs to Azure Monitor / Log Analytics workspaces. You can query tables like
       `ADFPipelineRun`, `ADFActivityRun`, and `ADFTriggerRun` using Kusto Query Language (KQL).

    Q: How do you track pipeline execution SLAs in ADF?
    A: 1. Configure alert rules in Azure Monitor based on duration metrics or failure events.
       2. Set `timeout` properties on individual activities or pipelines to force abort if runtime exceeds SLA.
"""

import logging, time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.adf_client import ADFClient

logger = logging.getLogger(__name__)


class PipelineMonitor:
    """
    Monitor for tracking ADF pipeline execution, activity runs, SLA compliance, and Log Analytics queries.
    """

    def __init__(self, client: ADFClient) -> None:
        """
        Initialize with ADFClient.

        Args:
            client: Authenticated ADFClient instance
        """
        self.client = client

    def get_pipeline_run(self, resource_group: str, factory_name: str, run_id: str) -> Dict[str, Any]:
        """
        Get current status and execution details of a pipeline run.

        Args:
            resource_group: Resource group name
            factory_name: ADF factory name
            run_id: Pipeline Run ID GUID

        Returns:
            Run status payload dict
        """
        if self.client.config.mock_mode:
            return {
                "run_id": run_id,
                "pipeline_name": "PL_Copy_BlobToADLS",
                "status": "Succeeded",
                "start_time": "2026-07-20T20:00:00Z",
                "end_time": "2026-07-20T20:02:15Z",
                "duration_ms": 135000,
                "parameters": {"SourceContainer": "raw"},
                "message": "",
            }

        adf = self.client.get_management_client()
        run = adf.pipeline_runs.get(
            resource_group_name=resource_group,
            factory_name=factory_name,
            run_id=run_id,
        )

        duration = None
        if run.run_start and run.run_end:
            duration = int((run.run_end - run.run_start).total_seconds() * 1000)

        return {
            "run_id": run.run_id,
            "pipeline_name": run.pipeline_name,
            "status": run.status,  # 'InProgress', 'Succeeded', 'Failed', 'Canceling', 'Cancelled'
            "start_time": run.run_start.isoformat() if run.run_start else None,
            "end_time": run.run_end.isoformat() if run.run_end else None,
            "duration_ms": duration,
            "parameters": run.parameters or {},
            "message": run.message or "",
        }

    def get_activity_runs(
        self,
        resource_group: str,
        factory_name: str,
        run_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get execution details of all activities executed within a pipeline run.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            run_id: Pipeline run ID
            start_time: Query window start (defaults to 1 day ago)
            end_time: Query window end (defaults to current time)

        Returns:
            List of activity execution detail dicts
        """
        now = datetime.utcnow()
        start = start_time or (now - timedelta(days=1))
        end = end_time or (now + timedelta(hours=1))

        if self.client.config.mock_mode:
            return [
                {
                    "activity_name": "CopyBlobToADLS",
                    "activity_type": "Copy",
                    "status": "Succeeded",
                    "duration_ms": 120000,
                    "error": None,
                    "input": {"SourceContainer": "raw"},
                    "output": {"dataRead": 1048576, "dataWritten": 512000, "rowsCopied": 5000},
                }
            ]

        adf = self.client.get_management_client()
        response = adf.activity_runs.query_by_pipeline_run(
            resource_group_name=resource_group,
            factory_name=factory_name,
            run_id=run_id,
            filter_parameters={
                "lastUpdatedAfter": start.isoformat() + "Z",
                "lastUpdatedBefore": end.isoformat() + "Z",
            },
        )

        activities = []
        for act in response.value:
            activities.append({
                "activity_name": act.activity_name,
                "activity_type": act.activity_type,
                "status": act.status,
                "duration_ms": act.duration_in_ms,
                "error": act.error,
                "input": act.input,
                "output": act.output,
            })

        return activities

    def get_failed_activity_runs(
        self,
        resource_group: str,
        factory_name: str,
        run_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract only failed activities from a pipeline run for root cause analysis.
        """
        activities = self.get_activity_runs(resource_group, factory_name, run_id)
        return [act for act in activities if act["status"] == "Failed"]

    def wait_for_completion(
        self,
        resource_group: str,
        factory_name: str,
        run_id: str,
        poll_interval_seconds: int = 10,
        timeout_seconds: int = 600,
    ) -> Dict[str, Any]:
        """
        Poll pipeline status until completion, timeout, or failure.

        Args:
            resource_group: Resource group
            factory_name: ADF factory name
            run_id: Pipeline run ID
            poll_interval_seconds: Polling sleep interval
            timeout_seconds: Maximum total wait time in seconds

        Returns:
            Final pipeline run status payload

        Raises:
            TimeoutError: If pipeline does not finish before timeout
        """
        logger.info("Waiting for pipeline run completion: %s (Timeout=%ds)", run_id, timeout_seconds)
        start_time = time.time()

        terminal_states = {"Succeeded", "Failed", "Cancelled"}

        while True:
            run_details = self.get_pipeline_run(resource_group, factory_name, run_id)
            status = run_details["status"]

            logger.info("Pipeline run %s status: %s", run_id, status)

            if status in terminal_states:
                logger.info("Pipeline run %s completed with status: %s", run_id, status)
                return run_details

            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutError(
                    f"Pipeline run {run_id} timed out after {elapsed:.1f}s. Last status: {status}"
                )

            time.sleep(poll_interval_seconds)

    def generate_kql_query_failed_pipelines(self, factory_name: str, days_back: int = 7) -> str:
        """
        Generate Log Analytics KQL query for finding failed pipeline runs over the past N days.

        Args:
            factory_name: Data Factory name filter
            days_back: Number of historical days

        Returns:
            KQL query string
        """
        return (
            f"ADFPipelineRun\n"
            f"| where TimeGenerated >= ago({days_back}d)\n"
            f"| where ResourceId contains '{factory_name}'\n"
            f"| where Status == 'Failed'\n"
            f"| project TimeGenerated, PipelineName, RunId, Status, Message, DurationMs = DurationInMs\n"
            f"| order by TimeGenerated desc"
        )

    def generate_kql_query_activity_performance(self, factory_name: str) -> str:
        """
        Generate KQL query for analyzing activity duration P95 / P99 metrics.

        Returns:
            KQL query string
        """
        return (
            f"ADFActivityRun\n"
            f"| where TimeGenerated >= ago(30d)\n"
            f"| where ResourceId contains '{factory_name}'\n"
            f"| summarize \n"
            f"    AvgDurationSeconds = avg(DurationInMs) / 1000.0,\n"
            f"    P95DurationSeconds = percentiles(DurationInMs, 95)[0] / 1000.0,\n"
            f"    TotalRuns = count(),\n"
            f"    FailureRate = countif(Status == 'Failed') * 100.0 / count()\n"
            f"  by ActivityName, ActivityType\n"
            f"| order by P95DurationSeconds desc"
        )
