"""
Repository Pattern for Data Engineering

Abstracts data access and provides a clean interface for data operations.
"""

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class DataRepository(ABC):
    """Abstract base class for data repositories."""

    @abstractmethod
    def fetch(self, query: str | None = None) -> pd.DataFrame:
        """Fetch data from source."""
        pass

    @abstractmethod
    def save(self, data: pd.DataFrame, table: str) -> int:
        """Save data to destination, returns row count."""
        pass

    @abstractmethod
    def exists(self, identifier: str) -> bool:
        """Check if resource exists."""
        pass


class CSVRepository(DataRepository):
    """Repository for CSV file operations."""

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    def fetch(self, query: str | None = None) -> pd.DataFrame:
        """Load CSV file into DataFrame."""
        filepath = f"{self.base_path}/{query}" if query else self.base_path
        return pd.read_csv(filepath)

    def save(self, data: pd.DataFrame, table: str) -> int:
        """Save DataFrame to CSV."""
        filepath = f"{self.base_path}/{table}.csv"
        data.to_csv(filepath, index=False)
        return len(data)

    def exists(self, identifier: str) -> bool:
        """Check if file exists."""
        import os
        filepath = f"{self.base_path}/{identifier}"
        return os.path.exists(filepath)


class DatabaseRepository(DataRepository):
    """Repository for database operations."""

    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self._connection: Any = None

    def fetch(self, query: str | None = None) -> pd.DataFrame:
        """Execute query and return DataFrame."""
        import sqlalchemy
        engine = sqlalchemy.create_engine(self.connection_string)
        return pd.read_sql(query or "SELECT 1", engine)

    def save(self, data: pd.DataFrame, table: str) -> int:
        """Save DataFrame to database table."""
        import sqlalchemy
        engine = sqlalchemy.create_engine(self.connection_string)
        data.to_sql(table, engine, if_exists="replace", index=False)
        return len(data)

    def exists(self, identifier: str) -> bool:
        """Check if table exists."""
        import sqlalchemy
        engine = sqlalchemy.create_engine(self.connection_string)
        return engine.dialect.has_table(engine, identifier)