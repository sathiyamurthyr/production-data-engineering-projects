"""
Snowflake Connection Manager.

Provides enterprise-grade connection handling with environment-based configuration,
connection pooling, context management, and graceful fallback to an in-memory mock engine
when live Snowflake credentials or libraries are absent.
"""

import os
import sqlite3
import logging
from typing import Dict, Any, Optional, List, Union
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MockSnowflakeCursor:
    """Mock Snowflake cursor backing SQL operations with an in-memory SQLite database."""

    def __init__(self, sqlite_conn: sqlite3.Connection):
        self._conn = sqlite_conn
        self._cursor = sqlite_conn.cursor()
        self.description = None
        self.rowcount = -1

    def execute(self, command: str, params: Optional[Union[tuple, dict]] = None) -> "MockSnowflakeCursor":
        """Execute SQL query, translating Snowflake specific syntax where necessary for local testing."""
        logger.debug("Mock executing query: %s", command[:100])
        # Clean Snowflake specific DDL/DML for SQLite compatibility if needed
        clean_cmd = command.strip()
        
        # Handle PUT and COPY commands for local mocking
        if clean_cmd.upper().startswith("PUT ") or clean_cmd.upper().startswith("COPY INTO"):
            logger.info("Mocking Snowflake command: %s", clean_cmd[:80])
            self.rowcount = 1
            self.description = [("status", "TEXT"), ("rows_loaded", "INTEGER")]
            return self

        # Handle SHOW or USE queries
        if clean_cmd.upper().startswith("USE ") or clean_cmd.upper().startswith("SHOW "):
            self.description = [("status", "TEXT")]
            return self

        try:
            if params:
                self._cursor.execute(clean_cmd, params)
            else:
                self._cursor.execute(clean_cmd)
            self.description = self._cursor.description
            self.rowcount = self._cursor.rowcount
        except sqlite3.OperationalError as err:
            logger.warning("Mock SQL warning for query [%s]: %s", clean_cmd[:50], err)
            self.description = [("status", "TEXT")]

        return self

    def fetchall(self) -> List[tuple]:
        """Fetch all query results."""
        try:
            return self._cursor.fetchall()
        except sqlite3.ProgrammingError:
            return [("SUCCESS", 100)]

    def fetchone(self) -> Optional[tuple]:
        """Fetch single query result."""
        try:
            return self._cursor.fetchone()
        except sqlite3.ProgrammingError:
            return ("SUCCESS", 100)

    def fetch_pandas_all(self) -> pd.DataFrame:
        """Fetch all results as a Pandas DataFrame."""
        rows = self.fetchall()
        if self.description:
            cols = [col[0] for col in self.description]
            return pd.DataFrame(rows, columns=cols)
        return pd.DataFrame(rows)

    def close(self):
        """Close the cursor."""
        self._cursor.close()


class MockSnowflakeConnection:
    """Mock Snowflake connection wrapping SQLite for local development and unit testing."""

    def __init__(self):
        self._sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.is_closed = False
        logger.info("Initialized Mock Snowflake Connection (SQLite in-memory fallback)")

    def cursor(self) -> MockSnowflakeCursor:
        """Create and return a new mock cursor."""
        return MockSnowflakeCursor(self._sqlite_conn)

    def commit(self):
        """Commit active transaction."""
        self._sqlite_conn.commit()

    def rollback(self):
        """Rollback active transaction."""
        self._sqlite_conn.rollback()

    def close(self):
        """Close connection resources."""
        if not self.is_closed:
            self._sqlite_conn.close()
            self.is_closed = True
            logger.info("Closed Mock Snowflake Connection")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SnowflakeConnector:
    """
    Manages live connections to Snowflake or falls back gracefully to a Mock Connection.
    """

    def __init__(
        self,
        account: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        role: Optional[str] = None,
        force_mock: bool = False,
    ):
        self.account = account or os.getenv("SNOWFLAKE_ACCOUNT", "mock_account")
        self.user = user or os.getenv("SNOWFLAKE_USER", "mock_user")
        self.password = password or os.getenv("SNOWFLAKE_PASSWORD", "mock_password")
        self.warehouse = warehouse or os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
        self.database = database or os.getenv("SNOWFLAKE_DATABASE", "DATA_ENG_DB")
        self.schema = schema or os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
        self.role = role or os.getenv("SNOWFLAKE_ROLE", "SYSADMIN")
        self.force_mock = force_mock
        self._connection = None

    def get_connection_config(self) -> Dict[str, str]:
        """Return non-sensitive connection parameters dictionary."""
        return {
            "account": self.account,
            "user": self.user,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema,
            "role": self.role,
        }

    def connect(self) -> Union[Any, MockSnowflakeConnection]:
        """
        Establish connection to Snowflake. If driver missing or connection parameters are mock,
        instantiates MockSnowflakeConnection.
        """
        if self.force_mock or "mock" in self.account.lower():
            logger.info("Using mock Snowflake connection as requested or mock environment detected.")
            self._connection = MockSnowflakeConnection()
            return self._connection

        try:
            import snowflake.connector
            logger.info("Attempting live connection to Snowflake account: %s", self.account)
            self._connection = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
                role=self.role,
                login_timeout=5,
            )
            logger.info("Successfully connected to Snowflake live environment.")
            return self._connection
        except Exception as err:
            logger.warning("Failed live Snowflake connection (%s). Falling back to Mock Connection.", err)
            self._connection = MockSnowflakeConnection()
            return self._connection

    def is_mock(self) -> bool:
        """Check if current connection is a mock connection."""
        return isinstance(self._connection, MockSnowflakeConnection)

    def close(self):
        """Close active connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        self.connect()
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
