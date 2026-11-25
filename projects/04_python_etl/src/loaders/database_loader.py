"""
Database Loader module for exporting DataFrames to relational SQL tables.
"""

from typing import Any, Dict
import pandas as pd
from sqlalchemy import create_engine

from src.loaders.base_loader import BaseLoader, LoadingError
from src.utils.file_utils import ensure_directory


class DatabaseLoader(BaseLoader):
    """Loader for persisting data into relational database tables via SQLAlchemy."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Database Loader.

        Config Keys:
            connection_string (str): SQLAlchemy database URI (e.g. 'sqlite:///warehouse.db').
            table_name (str): Target database table name.
            if_exists (str): Action if table exists ('append', 'replace', 'fail', default: 'append').
            chunk_size (int, optional): Batch size for database writes.
        """
        super().__init__(config)
        self.connection_string = config.get("connection_string", "")
        self.table_name = config.get("table_name", "etl_target_table")
        self.if_exists = config.get("if_exists", "append")
        self.chunksize = config.get("chunk_size", 1000)

    def load(self, df: pd.DataFrame) -> bool:
        """
        Insert DataFrame rows into target database table within a transaction.

        Args:
            df: Input DataFrame.

        Returns:
            bool: True on success.

        Raises:
            LoadingError: If database connection or insert execution fails.
        """
        if df is None:
            raise LoadingError("Cannot load None DataFrame into Database.")

        if not self.connection_string:
            raise LoadingError("Database connection_string must be specified.")

        try:
            # Ensure parent folder for SQLite db file if path based
            if self.connection_string.startswith("sqlite:///"):
                db_path = self.connection_string.replace("sqlite:///", "")
                if db_path != ":memory:":
                    ensure_directory(db_path)

            self.logger.info(
                f"Connecting to DB and inserting {len(df)} records into table '{self.table_name}' (if_exists='{self.if_exists}')"
            )
            engine = create_engine(self.connection_string)

            # Convert non-scalar columns to string representation for SQL storage
            df_to_save = df.copy()
            for col in df_to_save.columns:
                if df_to_save[col].apply(lambda val: isinstance(val, (list, dict))).any():
                    df_to_save[col] = df_to_save[col].astype(str)

            with engine.begin() as connection:
                df_to_save.to_sql(
                    name=self.table_name,
                    con=connection,
                    if_exists=self.if_exists,
                    index=False,
                    chunksize=self.chunksize,
                )

            self.logger.info(f"Database table '{self.table_name}' loaded successfully.")
            return True

        except Exception as e:
            msg = f"Failed to load DataFrame into table '{self.table_name}': {str(e)}"
            self.logger.error(msg)
            raise LoadingError(msg) from e
