"""
Query Executor Module for Advanced SQL for Data Engineering.
Provides a pythonic interface to run SQL files and raw queries against SQLite/PostgreSQL
returning results formatted as standard dictionaries.
"""

import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Union

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    """Convert SQLite row tuple to dictionary using column names."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class QueryExecutor:
    """Production Python SQL Executor wrapper around sqlite3."""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize database connection.

        Args:
            db_path: Path to sqlite database file or ':memory:' for transient DB.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = dict_factory
        logger.info(f"Initialized QueryExecutor with database target: {db_path}")

    def init_schema(self, ddl_path: str) -> None:
        """Execute schema DDL script from file.

        Args:
            ddl_path: Absolute or relative path to DDL SQL file.
        """
        if not os.path.exists(ddl_path):
            raise FileNotFoundError(f"Schema DDL file not found at path: {ddl_path}")

        with open(ddl_path, "r", encoding="utf-8") as f:
            ddl_script = f.read()

        self.conn.executescript(ddl_script)
        self.conn.commit()
        logger.info(f"Successfully applied schema DDL from {ddl_path}")

    def load_seed_data(self, seed_path: str) -> None:
        """Load seed dataset script from file.

        Args:
            seed_path: Absolute or relative path to Seed SQL file.
        """
        if not os.path.exists(seed_path):
            raise FileNotFoundError(f"Seed data file not found at path: {seed_path}")

        with open(seed_path, "r", encoding="utf-8") as f:
            seed_script = f.read()

        self.conn.executescript(seed_script)
        self.conn.commit()
        logger.info(f"Successfully loaded seed dataset from {seed_path}")

    def execute_query(self, sql_query: str, params: Union[tuple, dict] = ()) -> List[Dict[str, Any]]:
        """Execute a single SELECT or DML query returning dictionary rows.

        Args:
            sql_query: SQL query text.
            params: Parameters tuple/dict for SQL interpolation.

        Returns:
            List of dictionaries mapping column names to row values.
        """
        cursor = self.conn.cursor()
        cursor.execute(sql_query, params)
        if cursor.description is not None:
            results = cursor.fetchall()
        else:
            self.conn.commit()
            results = []
        return results

    def execute_script(self, sql_script: str) -> None:
        """Execute multiple SQL statements separated by semicolons.

        Args:
            sql_script: Raw SQL script text containing multiple statements.
        """
        self.conn.executescript(sql_script)
        self.conn.commit()

    def execute_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Execute SQL commands contained within a .sql file.

        Args:
            file_path: Path to SQL file to execute.

        Returns:
            List of dictionary results from the final SELECT query in the file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"SQL file not found at: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_sql = f.read()

        # Clean comments and filter to executable statements
        statements = [stmt.strip() for stmt in raw_sql.split(";") if stmt.strip()]

        last_results = []
        cursor = self.conn.cursor()

        for stmt in statements:
            # Skip pure comment blocks
            lines = [line.strip() for line in stmt.splitlines() if line.strip() and not line.strip().startswith("--")]
            if not lines:
                continue

            cleaned_stmt = "\n".join(lines)
            try:
                cursor.execute(cleaned_stmt)
                if cursor.description is not None:
                    last_results = cursor.fetchall()
                else:
                    self.conn.commit()
            except sqlite3.Error as err:
                logger.warning(f"Error executing statement block in {file_path}: {err}")
                continue

        return last_results

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Closed QueryExecutor database connection.")
