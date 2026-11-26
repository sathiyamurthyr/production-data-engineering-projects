"""
Unit Tests for Redshift Connector
=================================
Verifies connector configuration loading, mock connections, and cursor behaviors.
"""

import pytest
import os
import tempfile
import yaml
from src.redshift_connector import RedshiftConnector, MockRedshiftConnection, MockRedshiftCursor

@pytest.fixture
def temp_config_file():
    """Generates a temporary configuration YAML file."""
    config_data = {
        "redshift": {
            "host": "test-redshift-cluster.us-east-1.redshift.amazonaws.com",
            "port": 5439,
            "database": "testdb",
            "user": "testuser",
            "password": "testpassword",
            "iam_role_arn": "arn:aws:iam::123456789012:role/TestRole"
        }
    }
    
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, 'w') as tmp:
        yaml.dump(config_data, tmp)
        
    yield path
    os.remove(path)


def test_config_loading(temp_config_file):
    """Verifies that the YAML configuration is correctly loaded and parsed."""
    connector = RedshiftConnector(temp_config_file)
    assert connector.config["redshift"]["host"] == "test-redshift-cluster.us-east-1.redshift.amazonaws.com"
    assert connector.config["redshift"]["port"] == 5439
    assert connector.config["redshift"]["database"] == "testdb"
    assert connector.config["redshift"]["user"] == "testuser"
    assert connector.config["redshift"]["iam_role_arn"] == "arn:aws:iam::123456789012:role/TestRole"


def test_mock_fallback_on_invalid_credentials():
    """Verifies that the connector falls back to a Mock connection on failure."""
    # Using a non-existent config path will trigger the fallback
    connector = RedshiftConnector("non_existent_config.yaml")
    conn = connector.get_connection()
    
    assert isinstance(conn, MockRedshiftConnection)
    assert connector.mock_mode is True


def test_mock_cursor_queries():
    """Validates the behavior of MockRedshiftCursor execution and response simulation."""
    conn = MockRedshiftConnection()
    cursor = conn.cursor()
    
    # Test svv_table_info simulation
    cursor.execute("SELECT * FROM svv_table_info;")
    results = cursor.fetchall()
    
    assert len(results) == 3
    assert results[0][1] == "fact_sales"
    assert results[0][2] == 1500000 # Row count
    assert cursor.query_history[0][0] == "SELECT * FROM svv_table_info;"
    
    # Test svv_mv_info simulation
    cursor.execute("SELECT * FROM svv_mv_info;")
    mv_results = cursor.fetchall()
    assert len(mv_results) == 1
    assert mv_results[0][2] == "mv_customer_sales_summary"
    
    cursor.close()
    conn.close()
    assert conn.closed is True
