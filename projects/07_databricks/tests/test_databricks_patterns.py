"""
Unit Tests for Databricks Production Engineering Modules
"""

import pytest
from src.unity_catalog import UnityCatalogManager
from src.delta_live_tables import DLTPipelineBuilder, DLTExpectationMode
from src.databricks_jobs import DatabricksJobManager
from src.auto_loader import AutoLoaderIngestion
from src.structured_streaming import StructuredStreamingPipeline
from src.databricks_sql import DatabricksSQLConnector
from src.secrets_management import SecretsManager
from src.cluster_management import DatabricksClusterManager
from src.notebook_workflows import NotebookWorkflowOrchestrator
from src.performance_tuning import DatabricksPerformanceOptimizer
from src.mlflow_integration import MLflowTracker
from src.ci_cd_patterns import DatabricksAssetBundleGenerator


def test_unity_catalog_ddl_generation():
    uc = UnityCatalogManager()
    cat_sql = uc.create_catalog("prod_sales")
    schema_sql = uc.create_schema("prod_sales", "gold")
    grant_sql = uc.grant_privilege("analysts", "SELECT", "TABLE", "prod_sales.gold.orders")
    
    assert "CREATE CATALOG IF NOT EXISTS `prod_sales`" in cat_sql
    assert "CREATE SCHEMA IF NOT EXISTS `prod_sales`.`gold`" in schema_sql
    assert "GRANT SELECT ON TABLE prod_sales.gold.orders TO `analysts`" in grant_sql


def test_dlt_pipeline_builder():
    builder = DLTPipelineBuilder("unit_pipeline", "gold_schema")
    
    @builder.register_table("raw_table", "Raw table comment")
    def sample_table():
        return "SELECT 1"
        
    builder.add_expectation("raw_table", "valid_id", "id IS NOT NULL", DLTExpectationMode.FAIL)
    
    assert builder.validate_pipeline() is True
    assert len(builder.expectations["raw_table"]) == 1
    assert builder.expectations["raw_table"][0]["action"] == "FAIL"


def test_auto_loader_options():
    al = AutoLoaderIngestion(file_format="json", schema_location="/tmp/schema")
    opts = al.get_autoloader_options(schema_evolution_mode="addNewColumns", use_notifications=True)
    
    assert opts["cloudFiles.format"] == "json"
    assert opts["cloudFiles.schemaLocation"] == "/tmp/schema"
    assert opts["cloudFiles.useNotifications"] == "true"


def test_databricks_jobs_dag():
    jm = DatabricksJobManager()
    t1 = jm.create_notebook_task("t1", "/path/1")
    t2 = jm.create_notebook_task("t2", "/path/2", depends_on=["t1"])
    
    spec = jm.build_job_spec("test_job", [t1, t2])
    assert spec["name"] == "test_job"
    assert len(spec["tasks"]) == 2
    assert spec["tasks"][1]["depends_on"][0]["task_key"] == "t1"


def test_secrets_manager_fallback(monkeypatch):
    monkeypatch.setenv("PROD_SCOPE_API_KEY", "secret_env_12345")
    sm = SecretsManager(default_scope="prod_scope")
    secret = sm.get_secret("api_key")
    assert secret == "secret_env_12345"


def test_cluster_manager_spec():
    cm = DatabricksClusterManager()
    spec = cm.build_cluster_spec("test_cluster", min_workers=2, max_workers=8)
    assert spec["cluster_name"] == "test_cluster"
    assert spec["autoscale"]["min_workers"] == 2
    assert spec["autoscale"]["max_workers"] == 8


def test_performance_optimizer_configs():
    opt = DatabricksPerformanceOptimizer()
    configs = opt.get_optimized_spark_configs(enable_photon=True, enable_aqe=True)
    assert configs["spark.databricks.photon.enabled"] == "true"
    assert configs["spark.sql.adaptive.enabled"] == "true"


def test_ci_cd_bundle_generator():
    gen = DatabricksAssetBundleGenerator("my_bundle")
    yaml_str = gen.generate_databricks_yml()
    assert "name: my_bundle" in yaml_str
    assert "dev:" in yaml_str
    assert "prod:" in yaml_str
