"""
Unit tests for data loaders (CSV, Database, Parquet).
"""

from pathlib import Path
import pytest
import pandas as pd
from sqlalchemy import create_engine, text

from src.loaders.csv_loader import CSVLoader
from src.loaders.database_loader import DatabaseLoader
from src.loaders.parquet_loader import ParquetLoader
from src.loaders.base_loader import LoadingError


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Fixture returning sample DataFrame for loading tests."""
    return pd.DataFrame({
        "customer_id": ["C1", "C2", "C3"],
        "name": ["Alice", "Bob", "Charlie"],
        "total_spent": [500.0, 1200.5, 30.0]
    })


def test_csv_loader(tmp_path: Path, sample_df: pd.DataFrame):
    """Test CSV file writing."""
    csv_file = tmp_path / "output.csv"
    loader = CSVLoader({"path": str(csv_file), "index": False})

    assert loader.load(sample_df) is True
    assert csv_file.exists()

    read_back = pd.read_csv(csv_file)
    assert len(read_back) == 3
    assert list(read_back.columns) == ["customer_id", "name", "total_spent"]


def test_parquet_loader(tmp_path: Path, sample_df: pd.DataFrame):
    """Test Parquet columnar file writing."""
    parquet_file = tmp_path / "output.parquet"
    loader = ParquetLoader({"path": str(parquet_file), "compression": "snappy"})

    assert loader.load(sample_df) is True
    assert parquet_file.exists()

    read_back = pd.read_parquet(parquet_file)
    assert len(read_back) == 3
    assert read_back.iloc[0]["name"] == "Alice"


def test_database_loader(tmp_path: Path, sample_df: pd.DataFrame):
    """Test DatabaseLoader writing to SQLite database."""
    db_file = tmp_path / "warehouse.db"
    conn_str = f"sqlite:///{db_file}"

    loader = DatabaseLoader({
        "connection_string": conn_str,
        "table_name": "dim_customers",
        "if_exists": "replace"
    })

    assert loader.load(sample_df) is True

    engine = create_engine(conn_str)
    with engine.connect() as conn:
        result = pd.read_sql_query(text("SELECT * FROM dim_customers"), conn)
        assert len(result) == 3
        assert result.iloc[1]["customer_id"] == "C2"


def test_loader_none_dataframe():
    """Test loaders raise LoadingError when passed None."""
    loader = CSVLoader({"path": "out.csv"})
    with pytest.raises(LoadingError, match="Cannot load None DataFrame"):
        loader.load(None)
