"""
Pytest suite for Snowflake Connector, Utilities, ETL, and Cost Monitor.
"""

import pytest
import pandas as pd
from src.snowflake_connector import SnowflakeConnector, MockSnowflakeConnection
from src.snowflake_utils import SnowflakeUtils
from src.snowflake_etl import SnowflakeETLPipeline
from src.cost_monitor import SnowflakeCostMonitor


def test_snowflake_connector_init():
    """Test connection config extraction and properties."""
    connector = SnowflakeConnector(
        account="test_account",
        user="test_user",
        warehouse="TEST_WH",
        database="TEST_DB",
        schema="TEST_SCHEMA",
        role="TEST_ROLE",
        force_mock=True,
    )
    config = connector.get_connection_config()
    assert config["account"] == "test_account"
    assert config["user"] == "test_user"
    assert config["warehouse"] == "TEST_WH"
    assert config["database"] == "TEST_DB"
    assert config["schema"] == "TEST_SCHEMA"
    assert config["role"] == "TEST_ROLE"


def test_snowflake_connector_mock_context_manager():
    """Test context manager pattern and mock connection cursor operations."""
    connector = SnowflakeConnector(force_mock=True)
    with connector as conn:
        assert isinstance(conn, MockSnowflakeConnection)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_tbl (id INT, name TEXT);")
        cursor.execute("INSERT INTO test_tbl VALUES (1, 'Alice'), (2, 'Bob');")
        cursor.execute("SELECT * FROM test_tbl;")
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0] == (1, 'Alice')


def test_snowflake_connector_pandas_fetch():
    """Test fetching pandas DataFrame from cursor."""
    connector = SnowflakeConnector(force_mock=True)
    with connector as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE sales (id INT, amount FLOAT);")
        cursor.execute("INSERT INTO sales VALUES (101, 299.99), (102, 150.00);")
        cursor.execute("SELECT * FROM sales;")
        df = cursor.fetch_pandas_all()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2


def test_snowflake_utils_execute_and_script():
    """Test SnowflakeUtils query and multi-statement script execution."""
    connector = SnowflakeConnector(force_mock=True)
    utils = SnowflakeUtils(connector=connector)

    script = """
    CREATE TABLE dim_store (store_id VARCHAR, city VARCHAR);
    INSERT INTO dim_store VALUES ('S01', 'NYC'), ('S02', 'SF');
    SELECT * FROM dim_store;
    """
    results = utils.execute_script(script)
    assert len(results) == 3
    assert results[0]["status"] == "SUCCESS"

    wh_status = utils.get_warehouse_status("COMPUTE_WH")
    assert wh_status is not None


def test_snowflake_etl_pipeline_helpers():
    """Test stream and task generation in SnowflakeETLPipeline."""
    connector = SnowflakeConnector(force_mock=True)
    etl = SnowflakeETLPipeline(connector=connector)

    stream_res = etl.create_stream("STG_STREAM", "STG_TABLE", stream_type="APPEND_ONLY")
    assert stream_res["status"] == "CREATED"

    task_res = etl.create_task("REFRESH_TASK", "MERGE INTO target USING stream...", schedule_cron="USING CRON 0 * * * * UTC")
    assert task_res["status"] == "CREATED"

    resume_res = etl.resume_task("REFRESH_TASK")
    assert resume_res["status"] == "RESUMED"

    suspend_res = etl.suspend_task("REFRESH_TASK")
    assert suspend_res["status"] == "SUSPENDED"


def test_snowflake_cost_monitor():
    """Test SnowflakeCostMonitor resource monitor creation and rightsizing analysis."""
    connector = SnowflakeConnector(force_mock=True)
    monitor = SnowflakeCostMonitor(connector=connector)

    res = monitor.create_resource_monitor(
        monitor_name="DAILY_TEST_MONITOR",
        credit_quota=100,
        frequency="DAILY",
        notify_triggers=[50, 80],
        suspend_trigger=100,
    )
    assert res["status"] == "CREATED"
    assert res["credit_quota"] == 100

    suggestions = monitor.analyze_warehouse_right_sizing()
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
