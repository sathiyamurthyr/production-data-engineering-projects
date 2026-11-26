"""
Unit tests for EMR Cluster Lifecycle Client.
Uses unittest.mock to mock boto3 EMR client API responses.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import pytest
from unittest.mock import MagicMock, patch
from src.emr_client import EMRClusterManager


@pytest.fixture
def mock_emr_client():
    with patch("boto3.client") as mock_client:
        emr_mock = MagicMock()
        mock_client.return_value = emr_mock
        yield emr_mock


def test_create_cluster_success(mock_emr_client):
    # Setup mock return value
    mock_emr_client.run_job_flow.return_value = {"JobFlowId": "j-1234567890ABC"}
    
    manager = EMRClusterManager(region_name="us-east-1")
    config = {
        "Name": "test-cluster",
        "ReleaseLabel": "emr-6.13.0",
        "Instances": {},
        "ServiceRole": "EMR_DefaultRole",
        "JobFlowRole": "EMR_EC2_DefaultRole"
    }
    
    cluster_id = manager.create_cluster(config)
    assert cluster_id == "j-1234567890ABC"
    mock_emr_client.run_job_flow.assert_called_once_with(**config)


def test_create_cluster_missing_key():
    manager = EMRClusterManager(region_name="us-east-1")
    invalid_config = {
        "Name": "test-cluster"
        # Missing ReleaseLabel, Instances, ServiceRole, JobFlowRole
    }
    with pytest.raises(ValueError) as excinfo:
        manager.create_cluster(invalid_config)
    assert "Missing required configuration key" in str(excinfo.value)


def test_describe_cluster(mock_emr_client):
    mock_emr_client.describe_cluster.return_value = {
        "Cluster": {
            "Id": "j-1234567890ABC",
            "Name": "test-cluster",
            "Status": {"State": "WAITING"}
        }
    }
    
    manager = EMRClusterManager(region_name="us-east-1")
    details = manager.describe_cluster("j-1234567890ABC")
    
    assert details["Id"] == "j-1234567890ABC"
    assert details["Status"]["State"] == "WAITING"
    mock_emr_client.describe_cluster.assert_called_once_with(ClusterId="j-1234567890ABC")


def test_terminate_cluster(mock_emr_client):
    mock_emr_client.terminate_job_flows.return_value = {}
    
    manager = EMRClusterManager(region_name="us-east-1")
    manager.terminate_cluster("j-1234567890ABC")
    
    mock_emr_client.terminate_job_flows.assert_called_once_with(JobFlowIds=["j-1234567890ABC"])


@patch("time.sleep", return_value=None)  # Disable sleep to speed up test execution
def test_wait_for_cluster_state(mock_sleep, mock_emr_client):
    # Setup mock status to simulate transition from STARTING -> WAITING
    mock_emr_client.describe_cluster.side_effect = [
        {"Cluster": {"Status": {"State": "STARTING"}}},
        {"Cluster": {"Status": {"State": "BOOTSTRAPPING"}}},
        {"Cluster": {"Status": {"State": "WAITING"}}}
    ]
    
    manager = EMRClusterManager(region_name="us-east-1")
    final_state = manager.wait_for_cluster_state("j-1234567890ABC", target_states=["WAITING"], poll_interval=1)
    
    assert final_state == "WAITING"
    assert mock_emr_client.describe_cluster.call_count == 3
