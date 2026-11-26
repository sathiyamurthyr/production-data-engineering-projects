"""
Redshift Connector Module
=========================
Handles connection pooling or direct connection to Amazon Redshift cluster.
Provides fallback mocking capabilities when credentials or psycopg2 are missing.
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Try to import psycopg2
try:
    import psycopg2
    from psycopg2.extensions import connection as psycopg2_connection
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    psycopg2_connection = Any
    logger.warning("psycopg2 not found. RedshiftConnector will fall back to Mocking Mode.")


class MockRedshiftCursor:
    """Mock database cursor that simulates queries and records operations."""
    
    def __init__(self):
        self.query_history = []
        self.description = [("column", 1043, None, None, None, None, None)]
        self._results = []

    def execute(self, query: str, parameters: Optional[tuple] = None) -> None:
        """Records executed query and maps simulated responses."""
        q_lower = query.lower()
        self.query_history.append((query, parameters))
        logger.info(f"[MOCK SQL] Executed: {query} with params: {parameters}")
        
        # Populate simulated responses based on key keywords
        if "svv_table_info" in q_lower:
            self._results = [
                ("core", "fact_sales", 1500000, 5.2, 0.0, 128, 0.0),
                ("core", "dim_customer", 75000, 0.0, 1.2, 12, 0.0),
                ("staging", "staging_sales", 10000, 95.0, 85.0, 2, 0.0)
            ]
            self.description = [
                ("schemaname", 1043), ("tablename", 1043), ("tbl_rows", 23),
                ("unsorted", 701), ("stats_off", 701), ("size", 23), ("vacuum_sort_benefit", 701)
            ]
        elif "svv_mv_info" in q_lower:
            self._results = [
                ("dev", "core", "mv_customer_sales_summary", "f", "1", "t", "Incremental")
            ]
            self.description = [
                ("db_name", 1043), ("schema_name", 1043), ("mv_name", 1043),
                ("is_stale", 1043), ("state", 1043), ("autorefresh", 1043), ("refresh_type", 1043)
            ]
        elif "stl_wlm_query" in q_lower:
            self._results = [
                (6, 45, 0.12, 1.45, 12.5),
                (7, 12, 0.02, 0.15, 1.2)
            ]
            self.description = [
                ("queue_id", 23), ("total_queries", 23), ("avg_wait_seconds", 701),
                ("avg_exec_seconds", 701), ("max_exec_seconds", 701)
            ]
        elif "stl_qmr_rule" in q_lower:
            self._results = []
            self.description = [
                ("query_id", 23), ("rule_name", 1043), ("action", 1043),
                ("threshold_value", 20), ("actual_value", 20), ("query_text", 1043), ("event_time", 1114)
            ]
        elif "stl_alert_event_log" in q_lower:
            self._results = [
                (9999, 1, 0, 2, "Nested Loop", "2026-07-23 00:00:00", "Join loop costed too high")
            ]
            self.description = [
                ("query_id", 23), ("slice", 23), ("segment", 23), ("step", 23),
                ("alert_type", 1043), ("event_time", 1043), ("event_info", 1043)
            ]
        elif "select" in q_lower:
            self._results = [("mock_row_1",), ("mock_row_2",)]
        else:
            self._results = []

    def fetchall(self) -> list:
        return self._results

    def fetchone(self) -> Optional[tuple]:
        return self._results[0] if self._results else None

    def close(self) -> None:
        logger.info("[MOCK SQL] Cursor closed.")


class MockRedshiftConnection:
    """Mock database connection for local unit testing and fallbacks."""
    
    def __init__(self):
        self.closed = False

    def cursor(self) -> MockRedshiftCursor:
        return MockRedshiftCursor()

    def commit(self) -> None:
        logger.info("[MOCK SQL] Transaction committed.")

    def rollback(self) -> None:
        logger.info("[MOCK SQL] Transaction rolled back.")

    def close(self) -> None:
        self.closed = True
        logger.info("[MOCK SQL] Connection closed.")


class RedshiftConnector:
    """
    Manages connections to the Amazon Redshift Cluster.
    Uses YAML configuration. Falls back to mock connections if credentials fail or are absent.
    """
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.mock_mode = False

    def _load_config(self) -> Dict[str, Any]:
        """Loads configuration from YAML file."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config path {self.config_path} not found. Defaulting to mock configuration.")
            return {
                "redshift": {
                    "host": "localhost",
                    "port": 5439,
                    "database": "mock_db",
                    "user": "mock_user",
                    "password": "mock_password",
                    "iam_role_arn": "arn:aws:iam::123456789012:role/MockRole"
                }
            }
        
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)

    def get_connection(self) -> Union[psycopg2_connection, MockRedshiftConnection]:
        """
        Attempts to establish a live connection to Redshift.
        If psycopg2 is not installed or connection parameters fail, returns a Mock connection.
        """
        if not HAS_PSYCOPG2:
            logger.info("Using mock Redshift connection (psycopg2 not installed).")
            self.mock_mode = True
            return MockRedshiftConnection()

        creds = self.config.get("redshift", {})
        try:
            # Short timeout to avoid hanging during local tests
            conn = psycopg2.connect(
                host=creds.get("host"),
                port=creds.get("port", 5439),
                dbname=creds.get("database"),
                user=creds.get("user"),
                password=creds.get("password"),
                connect_timeout=3
            )
            logger.info("Successfully connected to live Redshift Cluster.")
            self.mock_mode = False
            return conn
        except Exception as e:
            logger.warning(f"Unable to connect to live Redshift cluster ({e}). Falling back to Mock connection.")
            self.mock_mode = True
            return MockRedshiftConnection()
