"""
Azure Data Factory (ADF) Databricks Activity Integration & Parameter Passing
=============================================================================
Production patterns for orchestrating Azure Databricks notebooks and Python jobs from ADF.

Business Use Case:
    In enterprise Azure architectures, Azure Data Factory serves as the central orchestrator
    for enterprise workflows (triggering file ingestion, checking dependencies, invoking Databricks
    for compute-heavy ETL, and triggering downstream Synapse/Power BI refresh). Databricks tasks
    must dynamically accept parameters passed from ADF, log execution status, and return standard
    JSON exit payloads to ADF for orchestration control flow.

Architecture:
    Azure Data Factory Workflow
    ├── Get Metadata / Storage Event Trigger
    ├── Databricks Notebook Activity
    │   ├── Pass parameters: run_id, execution_date, env, container
    │   └── Linked Service: Managed Identity / Key Vault Secret SP authentication
    ├── Databricks Exit Payload: {"status": "SUCCESS", "records_processed": 150000}
    └── Condition Check (If Success → Trigger Synapse / Send Notification)

Key Patterns:
    1. Parameter Extraction: Access ADF parameters inside notebook via dbutils.widgets.get()
    2. Exit Payloads: Return structured JSON results to ADF via dbutils.notebook.exit()
    3. Retries & Timeouts: Configure ADF activity retry policies and Databricks cluster timeout
    4. Linked Service Auth: Use Managed Identity or Service Principal stored in Azure Key Vault

Performance Notes:
    - Prefer Job Clusters (ephemeral clusters created per run) over Interactive clusters for ADF jobs.
      Job clusters are ~40% cheaper (lower DBU rates) and start isolated.
    - Warm up cluster pool if startup latency (< 2 min) is critical for tight SLAs.

Common Mistakes:
    - Returning plain strings instead of JSON in `dbutils.notebook.exit()`, making ADF parse steps fail.
    - hardcoding default parameters inside Databricks widgets without fallback handling.
    - Using interactive clusters in production ADF pipelines leading to higher costs and resource contention.

Interview Questions:
    Q: How do you pass dynamic parameters from Azure Data Factory to an Azure Databricks notebook?
    A: Define `baseParameters` in the ADF Databricks Notebook Activity JSON. Inside Databricks,
       use `dbutils.widgets.get("parameter_name")` to parse passed values dynamically at runtime.

    Q: How does ADF know if a Databricks Notebook activity succeeded or failed?
    A: If the Databricks notebook raises an uncaught exception, Databricks reports execution failure
       to ADF. If structured data needs to be passed back, `dbutils.notebook.exit(json_string)` is used.
       ADF can inspect activity output using `@activity('DatabricksNotebook').output.runOutput`.
"""

import json
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ADFDatabricksIntegration")


class ADFDatabricksHandler:
    """
    Handler for managing parameters, execution state, and exit payloads
    for Azure Data Factory (ADF) orchestrated Azure Databricks runs.
    """

    def __init__(self, dbutils: Optional[Any] = None):
        self.dbutils = dbutils
        self.params: Dict[str, Any] = {}

    def extract_adf_parameters(self, required_params: Optional[list] = None) -> Dict[str, Any]:
        """
        Extract parameters passed from ADF via Databricks widgets.
        
        Args:
            required_params: List of parameter names expected from ADF.
            
        Returns:
            Dictionary of parameter names and extracted values.
        """
        logger.info("Extracting parameters passed from Azure Data Factory...")
        expected = required_params or ["pipeline_run_id", "execution_date", "environment", "storage_account", "raw_container"]
        extracted = {}

        if self.dbutils is not None:
            for param in expected:
                try:
                    # In Databricks notebooks, widgets are declared or queried via dbutils
                    value = self.dbutils.widgets.get(param)
                    extracted[param] = value
                    logger.info(f"Retrieved ADF parameter '{param}': {value}")
                except Exception as e:
                    logger.warning(f"Parameter '{param}' not found in dbutils.widgets. Using fallback. Error: {e}")
                    extracted[param] = self._get_default_fallback(param)
        else:
            logger.info("dbutils not detected. Operating in local mode with mock ADF parameters.")
            extracted = {
                "pipeline_run_id": "adf-run-998877665544",
                "execution_date": "2026-07-20",
                "environment": "prod",
                "storage_account": "stmedallionprod",
                "raw_container": "raw",
                "trigger_type": "ScheduledTrigger"
            }

        self.params = extracted
        return extracted

    def _get_default_fallback(self, param_name: str) -> str:
        """Provide sensible defaults when running interactive tests without ADF parameters."""
        defaults = {
            "pipeline_run_id": "dev-local-run",
            "execution_date": "2026-01-01",
            "environment": "dev",
            "storage_account": "stmedalliondev",
            "raw_container": "raw-landing",
            "batch_size": "50000"
        }
        return defaults.get(param_name, "default_val")

    def exit_notebook_with_status(
        self,
        status: str,
        records_processed: int,
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> str:
        """
        Format standardized exit JSON payload and transmit back to ADF via dbutils.notebook.exit().
        
        Args:
            status: "SUCCESS" or "FAILED"
            records_processed: Total number of rows processed in job
            metrics: Optional dict of metrics (data quality score, processing duration)
            error_message: Details if status is FAILED
            
        Returns:
            Serialized JSON payload string.
        """
        payload = {
            "status": status,
            "pipeline_run_id": self.params.get("pipeline_run_id", "unknown"),
            "execution_date": self.params.get("execution_date", "unknown"),
            "records_processed": records_processed,
            "metrics": metrics or {},
            "error_message": error_message
        }
        
        json_output = json.dumps(payload)
        logger.info(f"Prepared ADF Exit Payload: {json_output}")

        if self.dbutils is not None:
            try:
                logger.info("Exiting Databricks notebook with payload for ADF.")
                self.dbutils.notebook.exit(json_output)
            except Exception as e:
                logger.error(f"Error invoking dbutils.notebook.exit: {e}")
        else:
            logger.info("Simulating dbutils.notebook.exit() call.")

        return json_output

    @staticmethod
    def generate_adf_linked_service_json(
        domain: str,
        workspace_resource_id: str,
        cluster_id: Optional[str] = None,
        use_managed_identity: bool = True
    ) -> Dict[str, Any]:
        """
        Generate JSON definition for Azure Data Factory Azure Databricks Linked Service.
        
        Supports Azure Managed Identity (System or User Assigned) and Service Principal auth.
        """
        definition = {
            "name": "ls_azure_databricks_prod",
            "properties": {
                "type": "AzureDatabricks",
                "typeProperties": {
                    "domain": f"https://{domain}",
                    "workspaceResourceId": workspace_resource_id,
                }
            }
        }

        if use_managed_identity:
            definition["properties"]["typeProperties"]["authentication"] = "MSI"
        else:
            definition["properties"]["typeProperties"]["authentication"] = "ServicePrincipal"
            definition["properties"]["typeProperties"]["servicePrincipalId"] = "@activity('GetSecret').output.value"

        if cluster_id:
            definition["properties"]["typeProperties"]["existingClusterId"] = cluster_id
        else:
            # Ephemeral Job Cluster Configuration
            definition["properties"]["typeProperties"]["newClusterMode"] = "Standard"
            definition["properties"]["typeProperties"]["newClusterNodeType"] = "Standard_D4ds_v5"
            definition["properties"]["typeProperties"]["newClusterNumOfWorker"] = "2:8"
            definition["properties"]["typeProperties"]["newClusterSparkVersion"] = "14.3.x-scala2.12"

        return definition


if __name__ == "__main__":
    handler = ADFDatabricksHandler()
    params = handler.extract_adf_parameters()
    print("Extracted ADF Params:", params)
    exit_msg = handler.exit_notebook_with_status(
        status="SUCCESS",
        records_processed=125000,
        metrics={"duration_sec": 42.5, "data_quality_passed": True}
    )
    print("Exit Payload:", exit_msg)
