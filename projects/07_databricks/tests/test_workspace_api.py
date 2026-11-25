"""
Unit Tests for Module 02: Databricks Workspace API & SDK Wrapper
"""

import pytest
from unittest.mock import MagicMock, patch
from src.workspace_api import DatabricksWorkspaceClient, WorkspaceConfig


@pytest.fixture
def mock_workspace_config():
    return WorkspaceConfig(
        host="https://adb-123456789.azuredatabricks.net",
        token="mock_dapi_token_12345",
    )


def test_workspace_config_initialization(mock_workspace_config):
    assert mock_workspace_config.host == "https://adb-123456789.azuredatabricks.net"
    assert mock_workspace_config.token == "mock_dapi_token_12345"
    assert mock_workspace_config.timeout_seconds == 30


def test_workspace_client_init(mock_workspace_config):
    client = DatabricksWorkspaceClient(mock_workspace_config)
    assert client.config == mock_workspace_config
    assert client.is_mock is True


def test_list_clusters_mock_mode(mock_workspace_config):
    client = DatabricksWorkspaceClient(mock_workspace_config)
    clusters = client.list_clusters()
    assert isinstance(clusters, list)
    assert len(clusters) > 0
    assert "cluster_id" in clusters[0]
    assert "cluster_name" in clusters[0]


def test_create_job_payload(mock_workspace_config):
    client = DatabricksWorkspaceClient(mock_workspace_config)
    job_spec = client.create_job(
        name="unit_test_job",
        notebook_path="/Repos/dev/test_notebook",
        cron_schedule="0 0 12 * * ?",
    )
    assert job_spec["name"] == "unit_test_job"
    assert "tasks" in job_spec
    assert job_spec["tasks"][0]["notebook_task"]["notebook_path"] == "/Repos/dev/test_notebook"


def test_run_now(mock_workspace_config):
    client = DatabricksWorkspaceClient(mock_workspace_config)
    run_res = client.run_now(job_id=999, python_params={"env": "test"})
    assert "run_id" in run_res
    assert run_res["job_id"] == 999


def test_import_export_notebook_mock(mock_workspace_config):
    client = DatabricksWorkspaceClient(mock_workspace_config)
    exported = client.export_notebook("/Repos/dev/my_notebook")
    assert "display('Hello World')" in exported

    imported = client.import_notebook("/Repos/dev/new_notebook", content="print('test')")
    assert imported["path"] == "/Repos/dev/new_notebook"
    assert imported["status"] == "SUCCESS"
