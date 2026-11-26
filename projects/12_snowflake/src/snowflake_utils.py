"""
Snowflake Utility Helpers.

Provides helper routines for query execution, metadata and schema inspection,
SQL script execution, clustering statistics retrieval, and warehouse status monitoring.
"""

import logging
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from src.snowflake_connector import SnowflakeConnector

logger = logging.getLogger(__name__)


class SnowflakeUtils:
    """Helper utilities for interacting with Snowflake metadata and execution environments."""

    def __init__(self, connector: Optional[SnowflakeConnector] = None):
        self.connector = connector or SnowflakeConnector()

    def execute_query(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> List[tuple]:
        """
        Execute arbitrary SQL query and return fetched rows.

        :param sql: SQL text string
        :param params: Optional parameters
        :return: List of row tuples
        """
        with self.connector as conn:
            cursor = conn.cursor()
            logger.debug("Executing SQL: %s", sql[:100])
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.fetchall()

    def fetch_dataframe(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as Pandas DataFrame.

        :param sql: SQL statement
        :param params: Optional parameters
        :return: Pandas DataFrame containing result set
        """
        with self.connector as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.fetch_pandas_all()

    def list_tables(self, schema_name: Optional[str] = None) -> pd.DataFrame:
        """List tables in specified schema or current active schema."""
        schema_clause = f"IN SCHEMA {schema_name}" if schema_name else ""
        sql = f"SHOW TABLES {schema_clause};"
        return self.fetch_dataframe(sql)

    def check_table_exists(self, table_name: str, schema_name: Optional[str] = None) -> bool:
        """Check if table exists in active context."""
        try:
            sql = f"DESCRIBE TABLE {table_name};"
            self.execute_query(sql)
            return True
        except Exception:
            return False

    def inspect_schema(self, table_name: str) -> pd.DataFrame:
        """Return schema column definitions for a table."""
        sql = f"DESCRIBE TABLE {table_name};"
        return self.fetch_dataframe(sql)

    def execute_script(self, script_text: str) -> List[Dict[str, Any]]:
        """
        Execute multi-statement SQL script string sequentially.

        :param script_text: Multi-statement SQL text separated by semicolons
        :return: Execution summary for each statement
        """
        results = []
        statements = [stmt.strip() for stmt in script_text.split(";") if stmt.strip()]
        with self.connector as conn:
            cursor = conn.cursor()
            for idx, stmt in enumerate(statements, 1):
                logger.info("Executing statement %d/%d: %s", idx, len(statements), stmt[:60])
                try:
                    cursor.execute(stmt)
                    rows = cursor.fetchall()
                    results.append({"index": idx, "statement": stmt[:60], "status": "SUCCESS", "rows": len(rows)})
                except Exception as err:
                    logger.error("Error executing statement %d: %s", idx, err)
                    results.append({"index": idx, "statement": stmt[:60], "status": "FAILED", "error": str(err)})
        return results

    def get_clustering_information(self, table_name: str) -> str:
        """Retrieve micro-partition clustering health metrics for a table."""
        sql = f"SELECT SYSTEM$CLUSTERING_INFORMATION('{table_name}');"
        rows = self.execute_query(sql)
        if rows:
            return str(rows[0][0])
        return "{}"

    def get_warehouse_status(self, warehouse_name: str) -> str:
        """Retrieve state of virtual warehouse ('RUNNING', 'SUSPENDED', etc.)."""
        sql = f"SELECT SYSTEM$WAREHOUSE_STATUS('{warehouse_name}');"
        try:
            rows = self.execute_query(sql)
            return str(rows[0][0]) if rows else "UNKNOWN"
        except Exception:
            return "UNKNOWN"
