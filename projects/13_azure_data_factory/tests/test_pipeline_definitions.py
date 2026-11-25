"""
test_pipeline_definitions.py - Integration & Unit Tests for ADF Resource Managers
===================================================================================
Tests for Linked Services, Datasets, Pipelines, Triggers, Monitoring, and Utilities.
"""

import os
import pytest
from src.adf_client import ADFClient, ADFConfig
from src.linked_services import LinkedServiceManager
from src.datasets import DatasetManager
from src.pipelines.copy_activity_pipeline import CopyActivityPipelineManager
from src.pipelines.mapping_dataflow_pipeline import MappingDataFlowPipelineManager
from src.pipelines.foreach_pipeline import ForEachPipelineManager
from src.pipelines.conditional_pipeline import ConditionalPipelineManager
from src.pipelines.trigger_management import TriggerManager
from src.monitoring import PipelineMonitor
from src.adf_utils import ADFUtils


@pytest.fixture
def mock_client():
    """Fixture returning an ADFClient in mock mode."""
    config = ADFConfig(
        tenant_id="00000000-0000-0000-0000-000000000000",
        client_id="00000000-0000-0000-0000-000000000000",
        client_secret="mock-secret",
        subscription_id="00000000-0000-0000-0000-000000000000",
        resource_group="rg-test",
        factory_name="adf-test",
        mock_mode=True,
    )
    return ADFClient(config)


def test_linked_service_manager(mock_client):
    """Test creating various Linked Services."""
    ls_mgr = LinkedServiceManager(mock_client)

    kv_ls = ls_mgr.create_key_vault_linked_service("rg-test", "adf-test", "KeyVaultLS", "https://kv.vault.azure.net/")
    assert kv_ls["name"] == "KeyVaultLS"

    blob_ls = ls_mgr.create_azure_blob_linked_service("rg-test", "adf-test", "BlobLS", connection_string="UseDevelopmentStorage=true")
    assert blob_ls["name"] == "BlobLS"

    adls_ls = ls_mgr.create_adls_gen2_linked_service("rg-test", "adf-test", "ADLSGen2LS", "https://mystorage.dfs.core.windows.net")
    assert adls_ls["name"] == "ADLSGen2LS"

    sql_ls = ls_mgr.create_azure_sql_linked_service("rg-test", "adf-test", "SqlLS", "server.database.windows.net", "db", "admin", "KeyVaultLS", "secret-pass")
    assert sql_ls["name"] == "SqlLS"

    snowflake_ls = ls_mgr.create_snowflake_linked_service("rg-test", "adf-test", "SnowflakeLS", "https://sf.snowflake.com", "user", "db", "wh", "KeyVaultLS", "secret-pass")
    assert snowflake_ls["name"] == "SnowflakeLS"

    services = ls_mgr.list_linked_services("rg-test", "adf-test")
    assert len(services) > 0


def test_dataset_manager(mock_client):
    """Test creating Parquet, CSV, JSON, SQL Datasets."""
    ds_mgr = DatasetManager(mock_client)

    pq_ds = ds_mgr.create_parquet_dataset("rg-test", "adf-test", "ParquetDS", "ADLSGen2LS", "gold", "sales")
    assert pq_ds["name"] == "ParquetDS"

    csv_ds = ds_mgr.create_csv_dataset("rg-test", "adf-test", "CsvDS", "BlobLS", "raw", "incoming")
    assert csv_ds["name"] == "CsvDS"

    json_ds = ds_mgr.create_json_dataset("rg-test", "adf-test", "JsonDS", "ADLSGen2LS", "logs", "raw")
    assert json_ds["name"] == "JsonDS"

    sql_ds = ds_mgr.create_azure_sql_table_dataset("rg-test", "adf-test", "SqlDS", "SqlLS", "Orders", "dbo")
    assert sql_ds["name"] == "SqlDS"


def test_copy_activity_pipeline_manager(mock_client):
    """Test Copy Activity Pipeline generation and execution."""
    mgr = CopyActivityPipelineManager(mock_client)

    spec = mgr.build_blob_to_adls_pipeline_spec("PL_Copy", "CsvDS", "ParquetDS")
    assert "activities" in spec["properties"]
    assert spec["properties"]["activities"][0]["type"] == "Copy"

    sql_spec = mgr.build_sql_to_parquet_pipeline_spec(
        "PL_SqlCopy", "SqlDS", "ParquetDS",
        column_mappings=[{"source": "OrderID", "target": "order_id"}]
    )
    assert len(sql_spec["properties"]["activities"]) > 0

    res = mgr.create_or_update_pipeline("rg-test", "adf-test", "PL_Copy", spec)
    assert res["name"] == "PL_Copy"

    run_id = mgr.trigger_pipeline_run("rg-test", "adf-test", "PL_Copy")
    assert run_id.startswith("run-")


def test_mapping_dataflow_pipeline_manager(mock_client):
    """Test Mapping Data Flow pipeline generation."""
    mgr = MappingDataFlowPipelineManager(mock_client)

    df_spec = mgr.build_sales_transformation_dataflow_spec("DF_Sales")
    assert "scriptLines" in df_spec["properties"]

    pl_spec = mgr.build_dataflow_pipeline_activity_spec("PL_DF", "DF_Sales")
    assert pl_spec["properties"]["activities"][0]["type"] == "ExecuteDataFlow"

    res = mgr.create_or_update_dataflow("rg-test", "adf-test", "DF_Sales", df_spec)
    assert res["name"] == "DF_Sales"

    run_id = mgr.trigger_dataflow_pipeline("rg-test", "adf-test", "PL_DF")
    assert run_id.startswith("run-df-")


def test_foreach_pipeline_manager(mock_client):
    """Test ForEach parallel pipeline creation."""
    mgr = ForEachPipelineManager(mock_client)

    spec = mgr.build_dynamic_multi_table_ingest_pipeline_spec("PL_Master", "ControlDS", "PL_Child", batch_count=10)
    assert len(spec["properties"]["activities"]) == 2
    assert spec["properties"]["activities"][1]["type"] == "ForEach"

    res = mgr.create_or_update_pipeline("rg-test", "adf-test", "PL_Master", spec)
    assert res["name"] == "PL_Master"


def test_conditional_pipeline_manager(mock_client):
    """Test Conditional logic pipeline creation."""
    mgr = ConditionalPipelineManager(mock_client)

    spec = mgr.build_conditional_ingest_pipeline_spec("PL_Cond", "SqlDS", "PL_Child")
    assert spec["properties"]["activities"][1]["type"] == "IfCondition"

    switch_spec = mgr.build_switch_routing_pipeline_spec("PL_Switch")
    assert switch_spec["properties"]["activities"][0]["type"] == "Switch"

    res = mgr.create_or_update_pipeline("rg-test", "adf-test", "PL_Cond", spec)
    assert res["name"] == "PL_Cond"


def test_trigger_manager(mock_client):
    """Test Schedule, Tumbling Window, and Storage Event triggers."""
    trg_mgr = TriggerManager(mock_client)

    sched = trg_mgr.create_schedule_trigger("rg-test", "adf-test", "TR_Sched", "PL_Copy")
    assert sched["name"] == "TR_Sched"

    tumbling = trg_mgr.create_tumbling_window_trigger("rg-test", "adf-test", "TR_Tumb", "PL_Copy")
    assert tumbling["name"] == "TR_Tumb"

    event_trg = trg_mgr.create_storage_event_trigger("rg-test", "adf-test", "TR_Event", "PL_Copy", "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/st")
    assert event_trg["name"] == "TR_Event"

    trg_mgr.start_trigger("rg-test", "adf-test", "TR_Sched")
    trg_mgr.stop_trigger("rg-test", "adf-test", "TR_Sched")


def test_pipeline_monitor(mock_client):
    """Test pipeline run monitoring and KQL generation."""
    monitor = PipelineMonitor(mock_client)

    run_info = monitor.get_pipeline_run("rg-test", "adf-test", "run-123")
    assert run_info["status"] == "Succeeded"

    activities = monitor.get_activity_runs("rg-test", "adf-test", "run-123")
    assert len(activities) > 0

    kql_failed = monitor.generate_kql_query_failed_pipelines("adf-test")
    assert "ADFPipelineRun" in kql_failed

    kql_perf = monitor.generate_kql_query_activity_performance("adf-test")
    assert "ADFActivityRun" in kql_perf


def test_adf_utils(tmp_path):
    """Test ADFUtils ARM template parameter generation and validation."""
    utils = ADFUtils()

    param_file = utils.generate_arm_parameter_file(
        factory_name="adf-test",
        key_vault_url="https://kv.vault.azure.net/",
        adls_endpoint="https://st.dfs.core.windows.net/",
    )
    assert param_file["parameters"]["factoryName"]["value"] == "adf-test"

    output_json = tmp_path / "params.json"
    utils.save_json(str(output_json), param_file)
    loaded = utils.load_json(str(output_json))
    assert loaded["parameters"]["factoryName"]["value"] == "adf-test"

    cmd = utils.build_az_cli_deployment_command("rg-test", "arm.json", "params.json", "deploy-1")
    assert "az deployment group create" in cmd
