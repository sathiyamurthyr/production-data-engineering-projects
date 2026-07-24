"""Comprehensive tests for Python fundamentals examples."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.examples import (
    # Variables & Types
    demonstrate_data_types,
    batch_size,
    # Operators
    filter_by_age,
    calculate_percentile,
    # Strings
    clean_column_name,
    extract_domain,
    # Lists
    process_batch,
    chunk_list,
    # Sets
    find_duplicate_emails,
    validate_countries,
    # Dicts
    aggregate_metrics,
    merge_configs,
    # DateTime
    get_date_range,
    format_timestamp,
    # List Comprehension
    filter_active_customers,
    # Exception Handling
    safe_read_csv,
    # JSON
    flatten_json,
    # Units
    calculate_average,
    # ETL
    mini_etl_pipeline,
)
from src.models import Customer, ETLJobConfig


class TestVariablesDataTypes:
    """Tests for variables and data types."""

    def test_demonstrate_data_types(self):
        """Test data types demonstration."""
        result = demonstrate_data_types()
        assert "record_count" in result
        assert result["record_count"] == 50000
        assert result["is_valid"] is True
        assert result["last_run"] is None


class TestOperators:
    """Tests for operators."""

    def test_filter_by_age(self):
        """Test age filtering."""
        assert filter_by_age(25, 18) is True
        assert filter_by_age(15, 18) is False

    def test_calculate_percentile(self):
        """Test percentile calculation."""
        assert calculate_percentile(25, 100) == 25.0
        assert calculate_percentile(50, 200) == 25.0


class TestStrings:
    """Tests for string operations."""

    def test_clean_column_name(self):
        """Test column name cleaning."""
        assert clean_column_name("First Name") == "first_name"
        assert clean_column_name("Email@Address#") == "emailaddress"

    def test_extract_domain(self):
        """Test domain extraction."""
        assert extract_domain("john@example.com") == "example.com"


class TestLists:
    """Tests for list operations."""

    def test_process_batch(self):
        """Test batch processing."""
        records = [
            {"id": 1, "status": "active", "timestamp": "2024-01-01"},
            {"id": 2, "status": "inactive", "timestamp": "2024-01-02"},
        ]
        result = process_batch(records)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_chunk_list(self):
        """Test list chunking."""
        data = list(range(10))
        chunks = chunk_list(data, 3)
        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]


class TestSets:
    """Tests for set operations."""

    def test_find_duplicate_emails(self):
        """Test duplicate email detection."""
        customers = [
            {"email": "a@test.com"},
            {"email": "b@test.com"},
            {"email": "a@test.com"},
        ]
        duplicates = find_duplicate_emails(customers)
        assert "a@test.com" in duplicates


class TestDictionaries:
    """Tests for dictionary operations."""

    def test_aggregate_metrics(self):
        """Test metrics aggregation."""
        records = [{"revenue": 100}, {"revenue": 200}]
        result = aggregate_metrics(records)
        assert result["total_revenue"] == 300

    def test_merge_configs(self):
        """Test config merging."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_configs(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}


class TestDateTime:
    """Tests for datetime operations."""

    def test_get_date_range(self):
        """Test date range calculation."""
        start, end = get_date_range(30)
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert start < end

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_timestamp(dt)
        assert result == "2024-01-15T10:30:00"


class TestExceptionHandling:
    """Tests for exception handling."""

    def test_safe_read_csv_file_not_found(self, tmp_path):
        """Test safe CSV reading with missing file."""
        result = safe_read_csv(tmp_path / "nonexistent.csv")
        assert result is None

    def test_safe_read_csv_success(self, tmp_path):
        """Test successful CSV reading."""
        csv_content = "col1,col2\n1,2\n3,4\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        result = safe_read_csv(csv_file)
        assert len(result) == 2


class TestListComprehension:
    """Tests for list comprehension."""

    def test_filter_active_customers(self):
        """Test customer filtering."""
        customers = [
            {"status": "active", "age": 25},
            {"status": "inactive", "age": 25},
            {"status": "active", "age": 15},
        ]
        result = filter_active_customers(customers)
        assert len(result) == 1


class TestJSON:
    """Tests for JSON operations."""

    def test_flatten_json(self):
        """Test JSON flattening."""
        nested = {"a": {"b": 1, "c": 2}, "d": 3}
        result = flatten_json(nested)
        assert result == {"a_b": 1, "a_c": 2, "d": 3}


class TestUnits:
    """Tests for utility functions."""

    def test_calculate_average(self):
        """Test average calculation."""
        assert calculate_average([10, 20, 30]) == 20.0

    def test_calculate_average_empty(self):
        """Test average with empty list."""
        with pytest.raises(ValueError):
            calculate_average([])


class TestModels:
    """Tests for Pydantic models."""

    def test_customer_model(self):
        """Test customer model creation."""
        customer = Customer(
            customer_id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            signup_date="2024-01-01",
            country="USA",
            age=30,
        )
        assert customer.full_name == "John Doe"

    def test_etl_job_config(self):
        """Test ETL job configuration."""
        config = ETLJobConfig(
            job_name="test_job",
            source_table="raw.customers",
            target_table="analytics.customers",
        )
        assert config.batch_size == 1000