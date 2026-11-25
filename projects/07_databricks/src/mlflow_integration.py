"""
Module 14: MLflow Integration — Experiment Tracking & Model Governance from Databricks
====================================================================================

Explanation:
    Databricks includes managed MLflow fully integrated with Unity Catalog, secret scopes,
    and notebook/job workflows. It provides experiment tracking, model registry, artifact storage,
    and lineage tracking across data engineering and machine learning pipelines.

Business Use Case:
    - Tracking data drift, row count metrics, and execution latency across nightly ETL job runs.
    - Versioning Machine Learning models directly inside Unity Catalog (`catalog.schema.model`).
    - Logging data validation reports, execution profiles, and schema diff artifacts.
    - Governance: registering model lineage from raw training Delta tables to deployed REST endpoints.

Architecture:
    Databricks Job Task / Notebook Execution
                      |
    MLflow Client API (`mlflow.log_params`, `mlflow.log_metrics`)
                      |
    +-------------------------------------------------------------+
    |                     Managed MLflow Service                  |
    |  +----------------------+        +-----------------------+  |
    |  | Experiment Tracking  |        | Unity Catalog Model   |  |
    |  | (Runs & Metrics)     |        | Registry              |  |
    |  +----------------------+        +-----------------------+  |
    +-------------------------------------------------------------+
                      |
             DBFS / S3 Managed Artifact Storage

Performance Notes:
    - Autologging (`mlflow.spark.autolog()`) automatically records Spark data sources, row counts, and schema.
    - End-to-end encryption for artifacts stored in Unity Catalog managed volumes.

Common Mistakes:
    - Forgetting to call `mlflow.end_run()` in custom scripts when not using `with mlflow.start_run():`.
    - Logging massive dataset DataFrames directly as MLflow artifacts (store path reference to Delta table instead).
    - Saving models to legacy Workspace Model Registry instead of Unity Catalog standard model paths.

Interview Questions:
    Q: How does MLflow Model Registry integrate with Unity Catalog in Databricks?
    A: In Unity Catalog, models are 3-tier securable objects (`catalog.schema.model_name`).
       This allows governing access to ML models using standard SQL `GRANT` and `REVOKE` privileges.

    Q: How can Data Engineers use MLflow tracking for ETL data quality monitoring?
    A: Data engineers log micro-batch metrics (e.g. `dropped_rows_count`, `null_rate`, `latency_ms`) to MLflow
       during job execution to track data health trends and set automated alert thresholds over time.
"""

import logging
import os
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MLflowTracker:
    """
    Production wrapper for logging pipeline execution metrics, parameters,
    data quality results, and registering models with MLflow in Databricks.
    """

    def __init__(self, experiment_name: str = "/Shared/data_engineering_pipeline_tracking"):
        self.experiment_name = experiment_name
        self.active_run_id: Optional[str] = None

    def start_pipeline_run(self, run_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """
        Starts an MLflow run for tracking a data pipeline task.
        """
        logger.info(f"Starting MLflow Run '{run_name}' under experiment '{self.experiment_name}'")
        try:
            import mlflow
            mlflow.set_experiment(self.experiment_name)
            run = mlflow.start_run(run_name=run_name, tags=tags or {})
            self.active_run_id = run.info.run_id
            return self.active_run_id
        except Exception as e:
            logger.warning(f"MLflow client unavailable or offline: {e}. Generating mock run_id.")
            self.active_run_id = "mock_run_id_9988776655"
            return self.active_run_id

    def log_pipeline_metrics(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None,
    ) -> bool:
        """
        Logs numerical data engineering metrics (e.g., input_row_count, error_count, duration_seconds).
        """
        logger.info(f"Logging MLflow metrics for run '{self.active_run_id}': {metrics}")
        try:
            import mlflow
            for key, val in metrics.items():
                mlflow.log_metric(key, val, step=step)
            return True
        except Exception as e:
            logger.warning(f"MLflow log_metrics fallback: {e}")
            return False

    def log_pipeline_params(self, params: Dict[str, Any]) -> bool:
        """
        Logs ETL parameters (e.g. source_path, target_table, batch_date, dbr_version).
        """
        logger.info(f"Logging MLflow parameters for run '{self.active_run_id}': {params}")
        try:
            import mlflow
            for key, val in params.items():
                mlflow.log_param(key, str(val))
            return True
        except Exception as e:
            logger.warning(f"MLflow log_params fallback: {e}")
            return False

    def end_pipeline_run(self, status: str = "FINISHED") -> None:
        """
        Ends the current active MLflow run.
        """
        logger.info(f"Ending MLflow run '{self.active_run_id}' with status '{status}'")
        try:
            import mlflow
            mlflow.end_run(status=status)
        except Exception:
            pass
        self.active_run_id = None

    def build_register_uc_model_code(self, model_uri: str, catalog: str, schema: str, model_name: str) -> str:
        """
        Generates Python code to register an MLflow model into Unity Catalog 3-tier namespace.
        """
        full_name = f"{catalog}.{schema}.{model_name}"
        code = f"""
import mlflow

# Set Unity Catalog registry mode
mlflow.set_registry_uri("databricks-uc")

# Register model to 3-tier namespace
registered_model = mlflow.register_model(
    model_uri="{model_uri}",
    name="{full_name}"
)
print(f"Registered model into Unity Catalog: {{registered_model.name}} Version: {{registered_model.version}}")
"""
        return code.strip()


if __name__ == "__main__":
    tracker = MLflowTracker("/Shared/prod_etl_monitoring")

    run_id = tracker.start_pipeline_run("daily_silver_ingest", tags={"env": "prod", "pipeline": "sales"})

    tracker.log_pipeline_params({
        "source_format": "delta",
        "target_table": "prod_silver.fact_sales",
        "batch_date": "2026-07-20",
    })

    tracker.log_pipeline_metrics({
        "records_read": 1500000.0,
        "records_written": 1498200.0,
        "dropped_corrupt_records": 1800.0,
        "execution_duration_sec": 45.2,
    })

    tracker.end_pipeline_run()

    print("\n=== Unity Catalog Model Registration Code ===")
    print(tracker.build_register_uc_model_code(
        model_uri="runs:/mock_run_id/model",
        catalog="prod_ml",
        schema="sales_forecasting",
        model_name="demand_predictor",
    ))
