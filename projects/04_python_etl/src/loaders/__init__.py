"""
Loader module index exporting data target loading classes.
"""

from src.loaders.base_loader import BaseLoader, LoadingError
from src.loaders.csv_loader import CSVLoader
from src.loaders.database_loader import DatabaseLoader
from src.loaders.parquet_loader import ParquetLoader

__all__ = [
    "BaseLoader",
    "LoadingError",
    "CSVLoader",
    "DatabaseLoader",
    "ParquetLoader",
]
