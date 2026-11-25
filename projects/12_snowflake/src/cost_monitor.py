"""
Snowflake Cost & Credit Optimization Monitor.

Monitors virtual warehouse compute credit consumption, storage costs, long-running expensive queries,
and automates resource monitor governance.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from src.snowflake_connector import SnowflakeConnector

logger = logging.getLogger(__name__)


class SnowflakeCostMonitor:
    """Monitors credit quotas, warehouse usage history, and query cost efficiency."""

    def __init__(self, connector: Optional[SnowflakeConnector] = None):
        self.connector = connector or SnowflakeConnector()

    def get_daily_credit_consumption(self, days: int = 30) -> pd.DataFrame:
        """
        Query warehouse metering history to compute daily credit usage.

        :param days: Lookback period in days
        :return: DataFrame with columns [usage_date, warehouse_name, credits_used]
        """
        sql = f"""
        SELECT
            DATE(start_time) AS usage_date,
            warehouse_name,
            ROUND(SUM(credits_used), 2) AS credits_used
        FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
        WHERE start_time >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        GROUP BY 1, 2
        ORDER BY usage_date DESC, credits_used DESC;
        """
        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Fetching daily credit consumption for past %d days", days)
            cursor.execute(sql)
            return cursor.fetch_pandas_all()

    def get_top_expensive_queries(self, limit: int = 10) -> pd.DataFrame:
        """
        Identify top longest running / highest resource consuming queries.

        :param limit: Maximum queries to return
        :return: DataFrame of expensive queries
        """
        sql = f"""
        SELECT
            query_id,
            user_name,
            warehouse_name,
            warehouse_size,
            execution_time / 1000 AS execution_time_seconds,
            total_elapsed_time / 1000 AS total_elapsed_seconds,
            bytes_scanned,
            bytes_spilled_to_local_storage,
            bytes_spilled_to_remote_storage,
            LEFT(query_text, 100) AS truncated_query
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE execution_status = 'SUCCESS'
          AND start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        ORDER BY execution_time DESC
        LIMIT {limit};
        """
        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Fetching top %d expensive queries", limit)
            cursor.execute(sql)
            return cursor.fetch_pandas_all()

    def get_storage_cost_summary(self) -> pd.DataFrame:
        """Query storage usage metrics (Database storage, Fail-Safe, and Stage storage)."""
        sql = """
        SELECT
            usage_date,
            ROUND(storage_bytes / (1024*1024*1024), 2) AS database_storage_gb,
            ROUND(failsafe_bytes / (1024*1024*1024), 2) AS failsafe_storage_gb,
            ROUND(stage_bytes / (1024*1024*1024), 2) AS stage_storage_gb
        FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
        ORDER BY usage_date DESC
        LIMIT 30;
        """
        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Fetching storage usage summary")
            cursor.execute(sql)
            return cursor.fetch_pandas_all()

    def create_resource_monitor(
        self,
        monitor_name: str,
        credit_quota: int = 100,
        frequency: str = "MONTHLY",
        notify_triggers: Optional[List[int]] = None,
        suspend_trigger: int = 100,
        suspend_immediate_trigger: int = 110,
    ) -> Dict[str, Any]:
        """
        Create Resource Monitor to enforce hard/soft credit spending caps.

        :param monitor_name: Resource monitor name (e.g. DE_MONTHLY_MONITOR)
        :param credit_quota: Monthly/Daily credit quota
        :param frequency: 'MONTHLY', 'WEEKLY', 'DAILY', 'NEVER'
        :param notify_triggers: List of percentage thresholds to trigger notifications (e.g. [70, 85, 95])
        :param suspend_trigger: Percentage threshold to suspend warehouse for new queries
        :param suspend_immediate_trigger: Percentage threshold to kill running queries & suspend
        :return: Execution summary
        """
        notify_triggers = notify_triggers or [70, 85, 95]
        notify_clauses = " ".join([f"ON {t}% DO NOTIFY" for t in notify_triggers])

        sql = f"""
        CREATE OR REPLACE RESOURCE MONITOR {monitor_name}
        WITH CREDIT_QUOTA = {credit_quota}
        FREQUENCY = {frequency.upper()}
        START_TIMESTAMP = IMMEDIATELY
        {notify_clauses}
        ON {suspend_trigger}% DO SUSPEND
        ON {suspend_immediate_trigger}% DO SUSPEND_IMMEDIATE;
        """

        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Creating Resource Monitor: %s with quota %d credits", monitor_name, credit_quota)
            cursor.execute(sql)
            return {
                "monitor_name": monitor_name,
                "credit_quota": credit_quota,
                "frequency": frequency,
                "status": "CREATED",
            }

    def analyze_warehouse_right_sizing(self) -> List[Dict[str, Any]]:
        """
        Analyze warehouse load history to identify under-utilized or overloaded warehouses.
        """
        sql = """
        SELECT
            warehouse_name,
            COUNT(*) AS query_count,
            AVG(execution_time) AS avg_execution_ms,
            SUM(CASE WHEN bytes_spilled_to_remote_storage > 0 THEN 1 ELSE 0 END) AS spilled_queries
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE start_time >= DATEADD(day, -7, CURRENT_TIMESTAMP())
        GROUP BY 1;
        """
        suggestions = []
        with self.connector as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql)
                rows = cursor.fetchall()
                for row in rows:
                    wh_name, q_count, avg_exec, spilled = row[0], row[1], row[2], row[3]
                    recommendation = "Optimal"
                    if spilled > 0:
                        recommendation = "Upgrade Warehouse Size (Memory Spilling Detected)"
                    elif avg_exec < 100 and q_count < 50:
                        recommendation = "Downsize Warehouse or Reduce Auto-Suspend Timeout"
                    suggestions.append({
                        "warehouse_name": wh_name,
                        "query_count": q_count,
                        "avg_execution_ms": avg_exec,
                        "spilled_queries": spilled,
                        "recommendation": recommendation,
                    })
            except Exception as err:
                logger.warning("Could not execute account usage check: %s. Returning default recommendations.", err)
                suggestions.append({
                    "warehouse_name": "COMPUTE_WH",
                    "recommendation": "Set auto_suspend to 60s to avoid idle credit burn.",
                })
        return suggestions
