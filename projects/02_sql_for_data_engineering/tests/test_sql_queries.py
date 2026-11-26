"""
Unit and integration tests for Project 02: SQL for Data Engineering.
Validates execution of SQL queries against SQLite in-memory database.
"""

import sys
import sqlite3
from pathlib import Path
import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.query_runner import SQLQueryRunner

SCHEMA_FILE = PROJECT_DIR / "schemas" / "schema_ddl.sql"
SEED_FILE = PROJECT_DIR / "datasets" / "seed_data.sql"
QUERIES_DIR = PROJECT_DIR / "queries"


@pytest.fixture
def db_runner():
    """Fixture initializing an in-memory SQL database with schema and seed data."""
    runner = SQLQueryRunner(db_path=":memory:")
    runner.initialize_schema_and_seed(str(SCHEMA_FILE), str(SEED_FILE))
    yield runner
    runner.close()


def test_database_initialization(db_runner):
    """Test that schema and seed data load correctly into the database."""
    cursor = db_runner.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    assert "dim_customers" in tables
    assert "dim_products" in tables
    assert "fact_sales" in tables
    assert "audit_logs" in tables


def test_module_01_sql_fundamentals(db_runner):
    """Test query file m01_sql_fundamentals.sql."""
    results = db_runner.execute_query_file(str(QUERIES_DIR / "m01_sql_fundamentals.sql"))
    assert len(results) > 0


def test_module_08_aggregates(db_runner):
    """Test aggregate query file m08_aggregate_functions.sql."""
    results = db_runner.execute_query_file(str(QUERIES_DIR / "m08_aggregate_functions.sql"))
    assert len(results) > 0


def test_module_11_joins(db_runner):
    """Test joins query file m11_joins.sql."""
    results = db_runner.execute_query_file(str(QUERIES_DIR / "m11_joins.sql"))
    assert len(results) > 0


def test_module_25_window_functions(db_runner):
    """Test window function query file m25_window_functions.sql."""
    results = db_runner.execute_query_file(str(QUERIES_DIR / "m25_window_functions.sql"))
    assert len(results) > 0


def test_module_23_cte(db_runner):
    """Test CTE query file m23_cte.sql."""
    results = db_runner.execute_query_file(str(QUERIES_DIR / "m23_cte.sql"))
    assert len(results) > 0


def test_module_43_star_schema(db_runner):
    """Test star schema query file m43_star_schema.sql."""
    results = db_runner.execute_query_file(str(QUERIES_DIR / "m43_star_schema.sql"))
    assert len(results) > 0


def test_module_51_duplicate_detection(db_runner):
    """Test duplicate detection query file m51_duplicate_detection.sql."""
    results = db_runner.execute_query_file(str(QUERIES_DIR / "m51_duplicate_detection.sql"))
    assert isinstance(results, list)
