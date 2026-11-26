"""
Redshift Utilities Module
=========================
Contains analytical utilities for executing generic SQL queries, monitoring Redshift
table health, and detecting locking contentions in the database.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RedshiftUtils:
    """
    Assists data engineers with cluster administration duties including health reporting,
    lock investigations, and query executions.
    """
    
    def __init__(self, db_conn: Any):
        self.conn = db_conn

    def execute_sql(self, sql_query: str) -> List[tuple]:
        """
        Executes a SELECT query and returns the results.
        
        Args:
            sql_query: The SQL query to run
            
        Returns:
            List of rows as tuples
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql_query)
            results = cursor.fetchall()
            return results
        except Exception as e:
            logger.error(f"Error executing sql query: {e}")
            raise e
        finally:
            cursor.close()

    def get_table_health(self) -> List[Dict[str, Any]]:
        """
        Queries Redshift system catalog metadata (svv_table_info) to identify tables
        needing vacuum maintenance (high unsorted pct) or analyze runs (stats out of date).
        
        Returns:
            List of dictionaries with table health metrics
        """
        query = """
            SELECT 
                schemaname,
                tablename,
                tbl_rows,
                unsorted,
                stats_off,
                size,
                vacuum_sort_benefit
            FROM svv_table_info
            ORDER BY unsorted DESC;
        """
        
        raw_results = self.execute_sql(query)
        health_metrics = []
        for row in raw_results:
            health_metrics.append({
                "schema": row[0],
                "table": row[1],
                "rows": int(row[2]) if row[2] is not None else 0,
                "unsorted_pct": float(row[3]) if row[3] is not None else 0.0,
                "stats_off_pct": float(row[4]) if row[4] is not None else 0.0,
                "size_mb": int(row[5]) if row[5] is not None else 0,
                "vacuum_sort_benefit": float(row[6]) if row[6] is not None else 0.0
            })
        return health_metrics

    def monitor_locks(self) -> List[Dict[str, Any]]:
        """
        Scans transaction lock tables (stv_locks) to report write locks or blocked queries.
        
        Returns:
            List of dictionaries outlining active locks in the database.
        """
        # Note: In mock connection mode, this will execute and return empty list
        query = """
            SELECT 
                lock_owner_pid AS pid,
                lock_owner_tx AS transaction_id,
                relation AS table_oid,
                lock_mode,
                lock_status AS status,
                DATEDIFF('second', lock_time, GETDATE()) AS duration_seconds
            FROM stv_locks;
        """
        
        # We wrap this in try-except because stv_locks is provisioned cluster specific
        # and serverless might not support it, or mock mode might return mock structures.
        try:
            raw_results = self.execute_sql(query)
            locks = []
            for row in raw_results:
                locks.append({
                    "pid": row[0],
                    "transaction_id": row[1],
                    "table_oid": row[2],
                    "lock_mode": row[3],
                    "status": row[4],
                    "duration_seconds": row[5]
                })
            return locks
        except Exception as e:
            logger.warning(f"Failed to query stv_locks: {e}. Returning empty list.")
            return []
