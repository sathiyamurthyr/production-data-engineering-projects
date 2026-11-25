"""
DQ Metrics Tracker Module.

Persists time-series data quality metrics into a SQLite database, allowing data engineers
to track pass rates over time, dataset health trends, and failure frequency.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
import datetime
import pandas as pd

from src.dq_framework.quality_report import QualityReport

logger = logging.getLogger(__name__)


class DQMetricsTracker:
    """
    SQLite-backed metrics database manager for storing historical Data Quality execution metrics.
    """

    def __init__(self, db_path: str = "dq_metrics.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Establish connection to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize SQLite database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dataset_metrics (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    execution_timestamp TEXT NOT NULL,
                    execution_duration_seconds REAL NOT NULL,
                    total_records INTEGER NOT NULL,
                    total_rules INTEGER NOT NULL,
                    passed_rules INTEGER NOT NULL,
                    failed_rules INTEGER NOT NULL,
                    overall_pass_rate REAL NOT NULL,
                    critical_failures INTEGER NOT NULL,
                    error_failures INTEGER NOT NULL,
                    warning_failures INTEGER NOT NULL,
                    metrics_json TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rule_execution_history (
                    rule_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    dataset_name TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    failed_count INTEGER NOT NULL,
                    total_count INTEGER NOT NULL,
                    failed_percentage REAL NOT NULL,
                    execution_timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES dataset_metrics (run_id)
                );
            """)
            conn.commit()
            logger.debug(f"Initialized DQ Metrics DB schema at '{self.db_path}'.")

    def record_report(self, report: QualityReport) -> int:
        """
        Record a QualityReport execution into the metrics database.

        Args:
            report: Executed QualityReport instance.

        Returns:
            The generated `run_id` integer.
        """
        summary = report.summary_dict()
        critical_cnt = summary["severity_failures"]["CRITICAL"]
        error_cnt = summary["severity_failures"]["ERROR"]
        warning_cnt = summary["severity_failures"]["WARNING"]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dataset_metrics (
                    dataset_name, status, execution_timestamp, execution_duration_seconds,
                    total_records, total_rules, passed_rules, failed_rules,
                    overall_pass_rate, critical_failures, error_failures, warning_failures, metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    report.dataset_name,
                    report.status,
                    report.execution_timestamp,
                    report.execution_duration_seconds,
                    report.total_records,
                    report.total_rules,
                    report.passed_rules,
                    report.failed_rules,
                    report.overall_pass_rate,
                    critical_cnt,
                    error_cnt,
                    warning_cnt,
                    json.dumps(summary),
                ),
            )
            run_id = cursor.lastrowid

            # Insert detailed rule results
            rule_rows = []
            for r in report.results:
                rule_rows.append((
                    run_id,
                    report.dataset_name,
                    r.rule_name,
                    r.dimension.value,
                    r.severity.value,
                    1 if r.passed else 0,
                    r.failed_count,
                    r.total_count,
                    r.failed_percentage,
                    report.execution_timestamp,
                ))

            cursor.executemany(
                """
                INSERT INTO rule_execution_history (
                    run_id, dataset_name, rule_name, dimension, severity,
                    passed, failed_count, total_count, failed_percentage, execution_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rule_rows,
            )
            conn.commit()
            logger.info(f"Recorded QualityReport run_id={run_id} for dataset '{report.dataset_name}' in SQLite DB.")
            return run_id

    def get_dataset_history(self, dataset_name: str, limit: int = 30) -> pd.DataFrame:
        """Fetch historical runs for a dataset as a pandas DataFrame."""
        with self._get_connection() as conn:
            query = """
                SELECT run_id, dataset_name, status, execution_timestamp,
                       total_records, total_rules, passed_rules, failed_rules, overall_pass_rate
                FROM dataset_metrics
                WHERE dataset_name = ?
                ORDER BY run_id DESC
                LIMIT ?;
            """
            return pd.read_sql_query(query, conn, params=(dataset_name, limit))

    def get_frequent_failing_rules(self, dataset_name: Optional[str] = None, limit: int = 10) -> pd.DataFrame:
        """Identify rules that fail most frequently."""
        with self._get_connection() as conn:
            where_clause = "WHERE passed = 0"
            params = []
            if dataset_name:
                where_clause += " AND dataset_name = ?"
                params.append(dataset_name)
            params.append(limit)

            query = f"""
                SELECT rule_name, dimension, severity, COUNT(*) as failure_frequency,
                       AVG(failed_percentage) as avg_failed_pct
                FROM rule_execution_history
                {where_clause}
                GROUP BY rule_name, dimension, severity
                ORDER BY failure_frequency DESC
                LIMIT ?;
            """
            return pd.read_sql_query(query, conn, params=params)
