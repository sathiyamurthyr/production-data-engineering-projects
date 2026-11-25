"""
Azure Log Analytics & Diagnostic Logs Integration for Azure Databricks
======================================================================
Production implementation of observability, logging, and metrics forwarding
from Azure Databricks to Azure Monitor & Log Analytics.

Business Use Case:
    Enterprise data operations require centralized logging, proactive alerting,
    and governance tracking across all Databricks clusters and jobs. Databricks logs
    (Audit Logs, Driver Logs, System Logs) and application-level metrics must be
    streamed to Azure Log Analytics for monitoring SLAs, DBU cost anomalies, and pipeline errors.

Architecture:
    Azure Databricks Workspace
    ├── Audit Logs (AAD Auth, Secret Scope Access, Cluster Events)
    ├── Driver & Executor Logs (log4j, stdout, stderr)
    ├── Application Metrics (PySpark job metrics, throughput, record counts)
    │
    ▼ Diagnostic Settings
    Azure Log Analytics Workspace (Workspace-based Application Insights)
        ├── KQL Querying (Kusto Query Language)
        ├── Azure Monitor Alerts (PagerDuty / Email on pipeline failure)
        └── Power BI Observability Dashboard

Production Best Practices:
    - Forward Audit Logs to Log Analytics using Azure Diagnostic Settings.
    - Standardize log formatting (JSON struct) with standard fields: `timestamp`, `environment`, `pipeline_name`, `severity`, `trace_id`.
    - Use Log Analytics Data Collector API or Azure Monitor OpenTelemetry Exporter for custom metrics.
    - Set up retention policies in Log Analytics (e.g. 90 days hot, archivable to ADLS Gen2).

Interview Questions:
    Q: How do you capture Databricks audit logs in Azure?
    A: Configure Azure Diagnostic Settings on the Azure Databricks Workspace resource in Azure Portal
       or via Terraform/ARM template. Select `allLogs` (Audit, Jobs, Clusters) and target an Azure Log Analytics Workspace.

    Q: How do you query pipeline errors in Azure Log Analytics using KQL?
    A:
       DatabricksJobs
       | where TimeGenerated > ago(24h)
       | where ActionName == "runFailed" or Level == "ERROR"
       | project TimeGenerated, JobId, RunId, Message, ClusterId
"""

import json
import logging
import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AzureMonitorManager")


class AzureMonitorManager:
    """
    Manager for sending custom telemetry, structured operational logs,
    and metric heartbeats from Azure Databricks workloads to Azure Log Analytics / Azure Monitor.
    """

    def __init__(self, workspace_id: Optional[str] = None, shared_key: Optional[str] = None, env: str = "prod"):
        self.workspace_id = workspace_id or "00000000-0000-0000-0000-000000000000"
        self.shared_key = shared_key or "MOCK_SHARED_KEY_FROM_KEY_VAULT"
        self.env = env

    def log_pipeline_event(
        self,
        pipeline_name: str,
        stage: str,
        status: str,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create structured telemetry payload for ingestion into Azure Log Analytics custom log table (`DatabricksETL_CL`).
        """
        payload = {
            "TimeGenerated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Environment": self.env,
            "PipelineName": pipeline_name,
            "Stage": stage,
            "Status": status,
            "Message": message,
            "Metrics": metrics or {},
            "TraceId": trace_id or "N/A",
            "DatabricksClusterId": "0720-123456-mock123"
        }

        logger.info(f"Logging Event to Azure Log Analytics [{status}]: {pipeline_name} -> {stage} | {message}")
        self._send_to_azure_log_analytics(payload, log_type="DatabricksETL")
        return payload

    def _send_to_azure_log_analytics(self, payload: Dict[str, Any], log_type: str) -> bool:
        """
        Internal dispatcher sending HMAC-authenticated REST payload to Azure Log Analytics HTTP Data Collector API.
        """
        json_body = json.dumps(payload)
        logger.debug(f"Sending payload ({len(json_body)} bytes) to Log Analytics Workspace '{self.workspace_id}' (LogType: {log_type}_CL)")
        # In a real environment, executes Azure HTTP REST API POST with HMAC signature authorization header
        return True

    @staticmethod
    def get_sample_kql_queries() -> Dict[str, str]:
        """
        Provide collection of enterprise KQL (Kusto Query Language) queries for Databricks monitoring.
        """
        return {
            "failed_jobs_last_24h": """
                DatabricksJobs
                | where TimeGenerated > ago(24h)
                | where ActionName == "runFailed"
                | project TimeGenerated, JobId, RunId, WorkspaceId, Message
                | order by TimeGenerated desc
            """,
            "dbu_consumption_by_cluster": """
                DatabricksClusters
                | where TimeGenerated > ago(7d)
                | summarize TotalDBUs = sum(DBUQuantity) by ClusterName, ClusterId, bin(TimeGenerated, 1d)
                | render timechart
            """,
            "etl_latency_and_throughput": """
                DatabricksETL_CL
                | where TimeGenerated > ago(24h)
                | summarize 
                    AvgDurationSec = avg(todouble(Metrics.duration_sec)),
                    TotalRecords = sum(tolong(Metrics.records_processed))
                  by PipelineName_s, Stage_s
            """,
            "unauthorized_secret_access_attempts": """
                DatabricksAccounts
                | where TimeGenerated > ago(30d)
                | where ActionName in ("secretScopeRead", "secretScopeDelete")
                | where ResponseStatusCode != 200
                | project TimeGenerated, Identity, ActionName, RequestParams
            """
        }


if __name__ == "__main__":
    monitor = AzureMonitorManager(env="production")
    monitor.log_pipeline_event(
        pipeline_name="OrderIngestionETL",
        stage="SilverTransformation",
        status="SUCCESS",
        message="Processed 250,000 orders without data quality errors.",
        metrics={"records_processed": 250000, "duration_sec": 18.4, "data_quality_score": 0.998}
    )
    kql = monitor.get_sample_kql_queries()
    print("KQL Diagnostic Query Sample:")
    print(kql["failed_jobs_last_24h"])
