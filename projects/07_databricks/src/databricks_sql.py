"""
Module 09: Databricks SQL — Connector, REST API, & Warehouse Execution Patterns
==============================================================================

Explanation:
    Databricks SQL provides a high-performance serverless SQL engine built on top of Photon.
    The `databricks-sql-connector` Python library lets client applications connect to SQL Warehouses
    via HTTP path / Thrift protocol using standard PEP-249 DB-API interfaces.

Business Use Case:
    - Connecting web applications, dashboards (Superset, Tableau, PowerBI), or Python microservices to Databricks.
    - Low-latency interactive ad-hoc query execution against serverless SQL endpoints.
    - Automated query execution for BI data mart refreshing and metric computation.
    - Executing DDL/DML statements without instantiating heavy Spark clusters.

Architecture:
    Client App (Python / `databricks-sql-connector`)
                         |
           HTTPS / Thrift (Port 443)
                         |
           Databricks Serverless SQL Warehouse (Photon Engine)
                         |
            Unity Catalog & Delta Lake Storage

Performance Notes:
    - Serverless SQL Warehouses start up in < 10 seconds compared to 3-5 minutes for classic clusters.
    - Auto-stopping policy ensures warehouses stop after N minutes of inactivity (default 10 mins).
    - Setting `staging_allowed=True` enables fast binary fetch via arrow/cloud storage staging.

Common Mistakes:
    - Hardcoding server hostname and HTTP paths in repository code (use environment variables).
    - Executing long-running streaming queries against SQL Warehouses (SQL Warehouses are for SQL queries, not streaming).
    - Forgetting to close cursor/connection objects in try/finally blocks or context managers.

Interview Questions:
    Q: What is the difference between Serverless SQL Warehouses and Pro SQL Warehouses?
    A: Serverless SQL Warehouses are managed entirely by Databricks in their cloud account, offering instant startup (<10s),
       auto-scaling, and lower administrative overhead. Pro Warehouses run inside customer cloud accounts with longer start times.

    Q: How do you prevent SQL injection when executing dynamic queries via the Databricks SQL connector?
    A: Always use parameterized queries with `?` or `%s` parameter markers in the `.execute(sql, params)` method
       rather than raw string concatenation.
"""

import logging
import os
from typing import Dict, List, Optional, Any, Union

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabricksSQLConnector:
    """
    Production client for connecting to Databricks SQL Warehouses via databricks-sql-connector
    or REST API. Supports simulation mode for environments without active cloud connection.
    """

    def __init__(
        self,
        server_hostname: Optional[str] = None,
        http_path: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.server_hostname = server_hostname or os.getenv("DATABRICKS_HOST", "demo.cloud.databricks.com")
        self.http_path = http_path or os.getenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/ab1234567890cd")
        self.access_token = access_token or os.getenv("DATABRICKS_TOKEN", "dapi_mock_token")

    def execute_query_sql(
        self,
        query: str,
        parameters: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes a SQL query against the SQL Warehouse and returns rows as dictionaries.
        Supports parameter binding to prevent SQL injection.
        """
        logger.info(f"Executing SQL on warehouse ({self.http_path}): {query[:100]}...")

        # If databricks-sql is installed and valid credentials exist, attempt real execution
        try:
            from databricks import sql as dbsql
            connection = dbsql.connect(
                server_hostname=self.server_hostname,
                http_path=self.http_path,
                access_token=self.access_token,
            )
            with connection.cursor() as cursor:
                cursor.execute(query, parameters or ())
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                connection.close()
                return results
        except Exception as e:
            logger.warning(f"Connection failed or fallback to simulation mode: {e}")
            # Mock return result for demo / offline environment
            return [
                {"id": 1, "metric_name": "daily_active_users", "value": 15420, "event_date": "2026-07-20"},
                {"id": 2, "metric_name": "monthly_recurring_revenue", "value": 450000, "event_date": "2026-07-20"},
            ]

    def build_warehouse_config(
        self,
        name: str = "Analytics_Serverless_Warehouse",
        cluster_size: str = "Small",
        min_num_clusters: int = 1,
        max_num_clusters: int = 4,
        auto_stop_mins: int = 10,
    ) -> Dict[str, Any]:
        """
        Builds REST API payload for creating/configuring a SQL Warehouse (SQL Endpoint).
        """
        config = {
            "name": name,
            "cluster_size": cluster_size,
            "min_num_clusters": min_num_clusters,
            "max_num_clusters": max_num_clusters,
            "auto_stop_mins": auto_stop_mins,
            "enable_serverless_compute": True,
            "channel": {"name": "CHANNEL_NAME_CURRENT"},
        }
        logger.info(f"Built SQL Warehouse payload for '{name}' ({cluster_size})")
        return config


if __name__ == "__main__":
    connector = DatabricksSQLConnector()

    wh_config = connector.build_warehouse_config("prod_bi_warehouse", cluster_size="Medium")
    print("=== Warehouse Spec ===")
    print(wh_config)

    print("\n=== Executing Parameterized Query ===")
    sql = "SELECT id, metric_name, value, event_date FROM gold_metrics WHERE event_date = %s"
    rows = connector.execute_query_sql(sql, parameters=["2026-07-20"])
    for row in rows:
        print("Row:", row)
