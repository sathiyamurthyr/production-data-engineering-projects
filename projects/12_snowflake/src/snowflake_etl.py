"""
Snowflake Streams & Tasks ETL Pipeline.

Implements real-time / micro-batch Change Data Capture (CDC) pipelines using Snowflake Streams
and automated serverless / warehouse-based Tasks for incremental MERGE logic.
"""

import logging
from typing import Dict, Any, List, Optional
from src.snowflake_connector import SnowflakeConnector

logger = logging.getLogger(__name__)


class SnowflakeETLPipeline:
    """Orchestrates Snowflake Streams, Tasks, and Incremental Merge ETL Pipelines."""

    def __init__(self, connector: Optional[SnowflakeConnector] = None):
        self.connector = connector or SnowflakeConnector()

    def create_stream(
        self,
        stream_name: str,
        source_table: str,
        stream_type: str = "STANDARD",
    ) -> Dict[str, Any]:
        """
        Create Change Data Capture (CDC) Stream on a table or stage.

        :param stream_name: Stream identifier (e.g. STG_SALES_STREAM)
        :param source_table: Source table name
        :param stream_type: 'STANDARD', 'APPEND_ONLY', or 'INSERT_ONLY'
        :return: Execution status dictionary
        """
        stype_clause = ""
        if stream_type.upper() == "APPEND_ONLY":
            stype_clause = "APPEND_ONLY = TRUE"
        elif stream_type.upper() == "INSERT_ONLY":
            stype_clause = "INSERT_ONLY = TRUE"

        sql = f"CREATE OR REPLACE STREAM {stream_name} ON TABLE {source_table} {stype_clause};"
        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Creating Stream %s on %s (Type: %s)", stream_name, source_table, stream_type)
            cursor.execute(sql)
            return {"stream_name": stream_name, "source_table": source_table, "status": "CREATED"}

    def create_task(
        self,
        task_name: str,
        sql_statement: str,
        schedule_cron: str = "USING CRON 0 * * * * UTC",
        warehouse: str = "ETL_WH",
        stream_condition: Optional[str] = None,
        depends_on: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create scheduled Snowflake Task or child Task in DAG sequence.

        :param task_name: Task identifier
        :param sql_statement: DML or Stored Procedure call to execute
        :param schedule_cron: Cron schedule string
        :param warehouse: Compute warehouse
        :param stream_condition: Stream identifier for WHEN SYSTEM$STREAM_HAS_DATA(...) clause
        :param depends_on: Parent task name for DAG dependency
        :return: Status summary dictionary
        """
        wh_clause = f"WAREHOUSE = {warehouse}" if warehouse else "USER_TASK_MANAGED_INITIAL_WAREHOUSE_SIZE = 'XSMALL'"
        schedule_clause = f"SCHEDULE = '{schedule_cron}'" if not depends_on else ""
        after_clause = f"AFTER {depends_on}" if depends_on else ""
        when_clause = f"WHEN SYSTEM$STREAM_HAS_DATA('{stream_condition}')" if stream_condition else ""

        sql = f"""
        CREATE OR REPLACE TASK {task_name}
        {wh_clause}
        {schedule_clause}
        {after_clause}
        {when_clause}
        AS
        {sql_statement};
        """

        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Creating Task: %s", task_name)
            cursor.execute(sql)
            return {"task_name": task_name, "status": "CREATED", "schedule": schedule_cron}

    def resume_task(self, task_name: str) -> Dict[str, Any]:
        """Resume suspended task (Tasks are created in SUSPENDED state by default)."""
        sql = f"ALTER TASK {task_name} RESUME;"
        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Resuming Task: %s", task_name)
            cursor.execute(sql)
            return {"task_name": task_name, "status": "RESUMED"}

    def suspend_task(self, task_name: str) -> Dict[str, Any]:
        """Suspend running task."""
        sql = f"ALTER TASK {task_name} SUSPEND;"
        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Suspending Task: %s", task_name)
            cursor.execute(sql)
            return {"task_name": task_name, "status": "SUSPENDED"}

    def build_merge_statement(
        self,
        target_table: str,
        stream_name: str,
        join_keys: List[str],
        update_columns: List[str],
        insert_columns: List[str],
    ) -> str:
        """Construct ANSI-compliant MERGE INTO statement consuming Stream CDC data."""
        join_condition = " AND ".join([f"t.{k} = s.{k}" for k in join_keys])
        set_assignments = ", ".join([f"t.{col} = s.{col}" for col in update_columns])
        col_list = ", ".join(insert_columns)
        val_list = ", ".join([f"s.{col}" for col in insert_columns])

        merge_sql = f"""
        MERGE INTO {target_table} AS t
        USING {stream_name} AS s
        ON {join_condition}
        WHEN MATCHED AND s.METADATA$ACTION = 'DELETE' AND s.METADATA$ISUPDATE = FALSE THEN
            DELETE
        WHEN MATCHED AND s.METADATA$ACTION = 'INSERT' AND s.METADATA$ISUPDATE = TRUE THEN
            UPDATE SET {set_assignments}, updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED AND s.METADATA$ACTION = 'INSERT' AND s.METADATA$ISUPDATE = FALSE THEN
            INSERT ({col_list}, created_at)
            VALUES ({val_list}, CURRENT_TIMESTAMP());
        """
        return merge_sql.strip()

    def execute_incremental_merge(
        self,
        target_table: str,
        stream_name: str,
        join_keys: List[str],
        update_columns: List[str],
        insert_columns: List[str],
    ) -> Dict[str, Any]:
        """Execute stream-to-target MERGE logic manually or via worker job."""
        sql = self.build_merge_statement(
            target_table=target_table,
            stream_name=stream_name,
            join_keys=join_keys,
            update_columns=update_columns,
            insert_columns=insert_columns,
        )

        with self.connector as conn:
            cursor = conn.cursor()
            logger.info("Executing incremental MERGE for table %s from stream %s", target_table, stream_name)
            cursor.execute(sql)
            return {"target_table": target_table, "stream": stream_name, "status": "MERGED"}
