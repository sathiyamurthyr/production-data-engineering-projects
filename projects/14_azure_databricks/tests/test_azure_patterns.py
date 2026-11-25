"""
Unit Test Suite for Azure Databricks Data Engineering Patterns
================================================================
Comprehensive pytest unit tests covering ADLS Gen2, Key Vault, Unity Catalog,
ETL pipeline logic, ADF orchestration, Azure Monitor, Cost Optimization, Security, and DevOps.
"""

import json
import pytest
from unittest.mock import MagicMock

from src.adls_integration import ADLSGen2Manager
from src.azure_key_vault import AzureKeyVaultManager
from src.unity_catalog_azure import UnityCatalogAzureManager
from src.azure_etl_pipeline import AzureETLPipeline, AzureETLPipelineConfig
from src.adf_databricks import ADFDatabricksHandler
from src.monitoring_azure import AzureMonitorManager
from src.cost_optimization import CostOptimizationManager
from src.security_patterns import AzureSecurityPatternsManager
from src.devops_integration import DevOpsIntegrationManager


class TestADLSGen2Integration:
    """Test suite for ADLS Gen2 integration patterns."""

    def test_abfss_uri_construction(self):
        adls = ADLSGen2Manager(storage_account_name="stmedallionprod")
        uri = adls.get_abfss_path(container="bronze", directory_path="orders/2026")
        assert uri == "abfss://bronze@stmedallionprod.dfs.core.windows.net/orders/2026"

    def test_sp_spark_config_generation(self):
        adls = ADLSGen2Manager(
            storage_account_name="stmedallionprod",
            client_id="mock-client-id",
            client_secret="mock-client-secret",
            tenant_id="mock-tenant-id"
        )
        configs = adls.get_spark_service_principal_configs()
        assert configs["fs.azure.account.auth.type.stmedallionprod.dfs.core.windows.net"] == "OAuth"
        assert configs["fs.azure.account.oauth.client.id.stmedallionprod.dfs.core.windows.net"] == "mock-client-id"


class TestAzureKeyVaultIntegration:
    """Test suite for Azure Key Vault secret scope manager."""

    def test_secret_retrieval(self):
        kv_mgr = AzureKeyVaultManager(scope_name="akv-prod-scope")
        mock_dbutils = MagicMock()
        mock_dbutils.secrets.get.return_value = "secret-sql-password-123"

        secret_val = kv_mgr.get_secret(secret_name="synapse-sql-auth", dbutils=mock_dbutils)
        assert secret_val == "secret-sql-password-123"
        mock_dbutils.secrets.get.assert_called_once_with(scope="akv-prod-scope", key="synapse-sql-auth")

    def test_fallback_when_dbutils_missing(self):
        kv_mgr = AzureKeyVaultManager(scope_name="akv-prod-scope")
        secret_val = kv_mgr.get_secret(secret_name="synapse-sql-auth", dbutils=None)
        assert secret_val == "MOCK_SECRET_SYNAPSE-SQL-AUTH"


class TestUnityCatalogAzure:
    """Test suite for Azure Unity Catalog governance."""

    def test_external_location_sql_generation(self):
        uc_mgr = UnityCatalogAzureManager(catalog_name="prod_catalog")
        sql = uc_mgr.generate_create_external_location_sql(
            location_name="ext_bronze_landing",
            abfss_url="abfss://bronze@stmedallionprod.dfs.core.windows.net/",
            credential_name="access_connector_credential"
        )
        assert "CREATE EXTERNAL LOCATION IF NOT EXISTS ext_bronze_landing" in sql
        assert "access_connector_credential" in sql

    def test_grant_access_sql(self):
        uc_mgr = UnityCatalogAzureManager(catalog_name="prod_catalog")
        sql = uc_mgr.generate_grant_access_sql(
            principal="data_engineers_group",
            privilege="USE CATALOG",
            object_type="CATALOG",
            object_name="prod_catalog"
        )
        assert sql == "GRANT USE CATALOG ON CATALOG prod_catalog TO `data_engineers_group`;"


class TestAzureETLPipeline:
    """Test suite for Medallion ETL pipeline."""

    def test_etl_pipeline_config(self):
        config = AzureETLPipelineConfig(storage_account_name="sttest")
        uri = config.get_abfss_path("silver", "tables/orders")
        assert uri == "abfss://silver@sttest.dfs.core.windows.net/tables/orders"

    def test_pipeline_local_execution(self):
        pipeline = AzureETLPipeline()
        results = pipeline.run_pipeline()
        assert results["status"] == "SUCCESS"
        assert "execution_duration_sec" in results


class TestADFDatabricksHandler:
    """Test suite for Azure Data Factory integration."""

    def test_extract_adf_parameters_fallback(self):
        handler = ADFDatabricksHandler(dbutils=None)
        params = handler.extract_adf_parameters()
        assert params["pipeline_run_id"] == "adf-run-998877665544"
        assert params["environment"] == "prod"

    def test_exit_notebook_payload_formatting(self):
        handler = ADFDatabricksHandler(dbutils=None)
        payload_str = handler.exit_notebook_with_status(
            status="SUCCESS",
            records_processed=5000,
            metrics={"quality_pass": True}
        )
        payload = json.loads(payload_str)
        assert payload["status"] == "SUCCESS"
        assert payload["records_processed"] == 5000
        assert payload["metrics"]["quality_pass"] is True


class TestAzureMonitorManager:
    """Test suite for Azure Log Analytics monitoring."""

    def test_log_pipeline_event(self):
        monitor = AzureMonitorManager(env="test")
        event = monitor.log_pipeline_event(
            pipeline_name="UnitTestPipeline",
            stage="Bronze",
            status="SUCCESS",
            message="Test run successful"
        )
        assert event["Status"] == "SUCCESS"
        assert event["PipelineName"] == "UnitTestPipeline"
        assert event["Environment"] == "test"

    def test_kql_queries_retrieval(self):
        kql_map = AzureMonitorManager.get_sample_kql_queries()
        assert "failed_jobs_last_24h" in kql_map
        assert "DatabricksJobs" in kql_map["failed_jobs_last_24h"]


class TestCostOptimizationManager:
    """Test suite for cluster cost optimization and policy generator."""

    def test_cluster_cost_estimation(self):
        cost_mgr = CostOptimizationManager()
        estimate = cost_mgr.estimate_cluster_cost(
            vm_type="Standard_D4ds_v5",
            num_workers=4,
            duration_hours=5.0,
            is_job_cluster=True,
            use_spot_workers=True
        )
        assert estimate["num_workers"] == 4
        assert estimate["total_estimated_cost_usd"] > 0
        assert estimate["estimated_savings_percent"] > 0

    def test_cluster_policy_structure(self):
        cost_mgr = CostOptimizationManager()
        policy = cost_mgr.generate_cost_optimized_cluster_policy()
        assert "autotermination_minutes" in policy
        assert policy["autotermination_minutes"]["defaultValue"] == 20


class TestAzureSecurityPatternsManager:
    """Test suite for security patterns and VNet injection."""

    def test_vnet_injection_template(self):
        sec_mgr = AzureSecurityPatternsManager()
        template = sec_mgr.generate_vnet_injection_arm_template()
        assert template["workspace_security"]["enableNoPublicIp"] is True
        assert len(template["vnet"]["subnets"]) == 2

    def test_rbac_matrix_retrieval(self):
        matrix = AzureSecurityPatternsManager.get_security_rbac_matrix()
        assert len(matrix) >= 4
        assert any(role["Azure Role"] == "Storage Blob Data Contributor" for role in matrix)


class TestDevOpsIntegrationManager:
    """Test suite for Azure DevOps & Databricks Asset Bundles."""

    def test_dab_yaml_generation(self):
        devops_mgr = DevOpsIntegrationManager(project_name="14_azure_databricks")
        dab_yaml = devops_mgr.generate_databricks_asset_bundle_yaml()
        assert "bundle:" in dab_yaml
        assert "targets:" in dab_yaml
        assert "14_azure_databricks" in dab_yaml

    def test_azure_devops_yaml_generation(self):
        devops_mgr = DevOpsIntegrationManager()
        devops_yaml = devops_mgr.generate_azure_devops_pipeline_yaml()
        assert "trigger:" in devops_yaml
        assert "databricks bundle deploy" in devops_yaml
