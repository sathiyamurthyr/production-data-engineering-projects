"""
Production SQL Query Runner module for Data Engineering SQL verification.
Executes query files against SQLite in-memory or persistent databases.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)


class SQLQueryRunner:
    """Production SQL executor for local database testing and dataset querying."""

    def __init__(self, db_path: Optional[str] = ":memory:"):
        """Initialize SQLite database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info("Initialized SQLQueryRunner connected to %s", db_path)

    def initialize_schema_and_seed(self, schema_file: str, seed_file: str) -> None:
        """Load DDL schema and seed data into the database."""
        logger.info("Loading schema DDL from %s...", schema_file)
        schema_sql = Path(schema_file).read_text(encoding="utf-8")
        self.conn.executescript(schema_sql)

        logger.info("Loading seed data from %s...", seed_file)
        seed_sql = Path(seed_file).read_text(encoding="utf-8")
        self.conn.executescript(seed_sql)
        self.conn.commit()
        logger.info("Database initialized successfully.")

    def execute_query_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Execute a SQL file and return results as a list of dict rows."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found at: {file_path}")

        raw_sql = path.read_text(encoding="utf-8")
        
        # Strip header block comments if present
        clean_lines = []
        in_multiline_comment = False
        for line in raw_sql.splitlines():
            stripped = line.strip()
            if stripped.startswith("/*"):
                in_multiline_comment = True
                continue
            if in_multiline_comment:
                if "*/" in stripped:
                    in_multiline_comment = False
                continue
            if stripped.startswith("--"):
                continue
            if stripped:
                clean_lines.append(line)
        
        sql = "\n".join(clean_lines).strip()
        if not sql:
            logger.warning("No executable SQL statements found in %s", file_path)
            return []

        logger.info("Executing query file: %s", path.name)
        cursor = self.conn.cursor()
        cursor.execute(sql)
        if cursor.description is None:
            return []
        
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Closed database connection.")
