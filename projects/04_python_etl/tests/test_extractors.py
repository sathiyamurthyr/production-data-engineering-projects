"""
Unit tests for data extractors (CSV, JSON, API, Database).
"""

import json
from pathlib import Path
import pytest
import pandas as pd
from sqlalchemy import create_engine, text

from src.extractors.csv_extractor import CSVExtractor
from src.extractors.json_extractor import JSONExtractor
from src.extractors.api_extractor import APIExtractor
from src.extractors.database_extractor import DatabaseExtractor
from src.extractors.base_extractor import ExtractionError


def test_csv_extractor_success(tmp_path: Path):
    """Test standard CSV extraction."""
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("id,name,val\n1,Alice,10.5\n2,Bob,20.0\n", encoding="utf-8")

    extractor = CSVExtractor({"path": str(csv_file), "delimiter": ","})
    df = extractor.extract()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["id", "name", "val"]
    assert df.iloc[0]["name"] == "Alice"


def test_csv_extractor_file_not_found():
    """Test CSVExtractor raises ExtractionError on missing file."""
    extractor = CSVExtractor({"path": "non_existent_file.csv"})
    with pytest.raises(ExtractionError, match="CSV file not found"):
        extractor.extract()


def test_csv_extractor_chunks(tmp_path: Path):
    """Test CSV extraction in chunks."""
    csv_file = tmp_path / "large.csv"
    lines = ["id,val\n"] + [f"{i},{i*10}\n" for i in range(10)]
    csv_file.write_text("".join(lines), encoding="utf-8")

    extractor = CSVExtractor({"path": str(csv_file), "chunk_size": 3})
    chunks = list(extractor.extract_chunks())

    assert len(chunks) == 4  # 10 rows in chunks of 3 -> 3+3+3+1
    assert len(chunks[0]) == 3


def test_json_extractor_records(tmp_path: Path):
    """Test JSON record list extraction."""
    json_file = tmp_path / "orders.json"
    data = [{"order_id": "O1", "amount": 100}, {"order_id": "O2", "amount": 250}]
    json_file.write_text(json.dumps(data), encoding="utf-8")

    extractor = JSONExtractor({"path": str(json_file)})
    df = extractor.extract()

    assert len(df) == 2
    assert "order_id" in df.columns
    assert df.iloc[1]["amount"] == 250


def test_api_extractor_mock():
    """Test APIExtractor using mock payload configuration."""
    mock_payload = {"rates": {"USD": 1.0, "EUR": 0.92, "GBP": 0.79}}
    extractor = APIExtractor({"mock_response": mock_payload})
    df = extractor.extract()

    assert len(df) == 1
    assert "EUR" in df.columns
    assert df.iloc[0]["EUR"] == 0.92


def test_database_extractor_sqlite(tmp_path: Path):
    """Test DatabaseExtractor querying SQLite table."""
    db_file = tmp_path / "test.db"
    conn_str = f"sqlite:///{db_file}"
    engine = create_engine(conn_str)

    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INT, username TEXT)"))
        conn.execute(text("INSERT INTO users VALUES (1, 'sathiya'), (2, 'murthy')"))
        conn.commit()

    extractor = DatabaseExtractor({
        "connection_string": conn_str,
        "table_name": "users"
    })
    df = extractor.extract()

    assert len(df) == 2
    assert list(df.columns) == ["id", "username"]
    assert df.iloc[0]["username"] == "sathiya"
