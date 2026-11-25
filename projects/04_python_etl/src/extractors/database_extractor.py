"""
Database Extractor module for reading from SQL databases via SQLAlchemy / SQLite.
"""

from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy import create_engine, text

from src.extractors.base_extractor import BaseExtractor, ExtractionError


class DatabaseExtractor(BaseExtractor):
    """Extractor for relational database tables and custom SQL queries."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Database Extractor.

        Config Keys:
            connection_string (str): Database URI (e.g. 'sqlite:///warehouse.db').
            query (str, optional): Custom SELECT SQL query string.
            table_name (str, optional): Name of table to extract if query is not specified.
            params (dict, optional): SQL query parameter bindings.
        """
        super().__init__(config)
        self.connection_string = config.get("connection_string", "")
        self.query = config.get("query")
        self.table_name = config.get("table_name")
        self.params = config.get("params", {})

    def extract(self) -> pd.DataFrame:
        """
        Execute SQL query or extract table into a DataFrame.

        Returns:
            pd.DataFrame: Query result dataset.

        Raises:
            ExtractionError: If connection fails or query syntax is invalid.
        """
        if not self.connection_string:
            raise ExtractionError("Database connection_string must be provided.")

        sql_statement = self.query
        if not sql_statement:
            if not self.table_name:
                raise ExtractionError("Either 'query' or 'table_name' must be configured.")
            sql_statement = f"SELECT * FROM {self.table_name}"

        try:
            self.logger.info(f"Connecting to database: {self.connection_string}")
            engine = create_engine(self.connection_string)

            with engine.connect() as connection:
                self.logger.info(f"Executing database extraction query: {sql_statement[:100]}...")
                df = pd.read_sql_query(
                    sql=text(sql_statement),
                    con=connection,
                    params=self.params
                )
                self.logger.info(f"Database query returned {len(df)} records.")
                return df

        except Exception as e:
            msg = f"Database extraction failed for '{self.connection_string}': {str(e)}"
            self.logger.error(msg)
            raise ExtractionError(msg) from e
