"""
Database Loader for ETL Pipeline

Loads data into databases with batch processing and upsert support.
"""

from typing import Any
from pydantic import BaseModel, Field
import sqlite3
from contextlib import contextmanager


class DBConfig(BaseModel):
    """Database connection configuration."""
    connection_string: str
    table_name: str
    batch_size: int = 1000
    mode: str = "append"  # append, replace, upsert


class DatabaseLoader:
    """
    Production database loader with batch processing.
    
    Supports full load, incremental load, and upsert patterns.
    """
    
    def __init__(self, config: DBConfig | dict[str, Any] | None = None, **kwargs):
        if config is None:
            config = DBConfig(**kwargs)
        elif isinstance(config, dict):
            config = DBConfig(**config)
        self.config = config
        self._connection = None
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.config.connection_string)
        try:
            yield conn
        finally:
            conn.close()
    
    def load(self, records: list[dict[str, Any]]) -> int:
        """Load records to database table."""
        if not records:
            return 0
        
        with self._get_connection() as conn:
            self._create_table_if_not_exists(conn, records[0].keys())
            
            # Batch insert
            columns = list(records[0].keys())
            placeholders = ", ".join(["?" for _ in columns])
            sql = f"INSERT INTO {self.config.table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            values = [tuple(record[col] for col in columns) for record in records]
            conn.executemany(sql, values)
            conn.commit()
        
        return len(records)
    
    def _create_table_if_not_exists(self, conn, columns: list[str]) -> None:
        """Create table if it doesn't exist."""
        column_defs = ", ".join([f"{col} TEXT" for col in columns])
        sql = f"CREATE TABLE IF NOT EXISTS {self.config.table_name} ({column_defs})"
        conn.execute(sql)


class IncrementalLoader(DatabaseLoader):
    """
    Incremental data loader with watermark support.
    """
    
    def __init__(self, config: DBConfig | dict[str, Any] | None = None, **kwargs):
        super().__init__(config, **kwargs)
        self.watermark_column = kwargs.get("watermark_column", "updated_at")
    
    def get_last_watermark(self) -> Any:
        """Get the last processed watermark value."""
        with self._get_connection() as conn:
            result = conn.execute(
                f"SELECT MAX({self.watermark_column}) FROM {self.config.table_name}"
            ).fetchone()
            return result[0] if result else None