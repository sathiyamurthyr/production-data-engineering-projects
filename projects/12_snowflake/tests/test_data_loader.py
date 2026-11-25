"""
Pytest suite for SnowflakeDataLoader pipeline operations.
"""

import os
import pytest
from src.snowflake_connector import SnowflakeConnector
from src.data_loader import SnowflakeDataLoader


@pytest.fixture
def sample_csv_file(tmp_path):
    """Fixture to generate a temporary CSV file for loading tests."""
    file_path = tmp_path / "test_sales.csv"
    content = "txn_id,amount,customer_id\nTX101,150.00,C001\nTX102,299.50,C002\n"
    file_path.write_text(content)
    return str(file_path)


def test_data_loader_stage_creation():
    """Test stage creation routines."""
    connector = SnowflakeConnector(force_mock=True)
    loader = SnowflakeDataLoader(connector=connector)

    res_int = loader.create_stage("TEST_INT_STAGE", stage_type="INTERNAL")
    assert res_int["status"] == "CREATED"
    assert res_int["stage_name"] == "TEST_INT_STAGE"

    res_ext = loader.create_stage(
        stage_name="TEST_EXT_STAGE",
        stage_type="EXTERNAL",
        s3_url="s3://my-test-bucket/data/",
        storage_integration="S3_INTEGRATION",
    )
    assert res_ext["status"] == "CREATED"


def test_data_loader_file_format():
    """Test creation of CSV, JSON, and PARQUET file formats."""
    connector = SnowflakeConnector(force_mock=True)
    loader = SnowflakeDataLoader(connector=connector)

    fmt_csv = loader.create_file_format("MY_CSV_FMT", format_type="CSV")
    assert fmt_csv["status"] == "CREATED"

    fmt_json = loader.create_file_format("MY_JSON_FMT", format_type="JSON")
    assert fmt_json["status"] == "CREATED"

    fmt_parquet = loader.create_file_format("MY_PARQUET_FMT", format_type="PARQUET")
    assert fmt_parquet["status"] == "CREATED"


def test_data_loader_upload_and_copy(sample_csv_file):
    """Test local PUT file upload and COPY INTO table execution."""
    connector = SnowflakeConnector(force_mock=True)
    loader = SnowflakeDataLoader(connector=connector)

    upload_res = loader.upload_file_to_stage(sample_csv_file, "TEST_INT_STAGE")
    assert upload_res["status"] == "UPLOADED"

    copy_res = loader.execute_copy_into(
        target_table="STG_TEST_SALES",
        stage_name="TEST_INT_STAGE",
        file_format_name="MY_CSV_FMT",
        on_error="CONTINUE",
    )
    assert copy_res["status"] == "COMPLETED"


def test_data_loader_load_csv_pipeline(sample_csv_file):
    """Test complete end-to-end load pipeline execution."""
    connector = SnowflakeConnector(force_mock=True)
    loader = SnowflakeDataLoader(connector=connector)

    res = loader.load_csv_pipeline(
        local_csv_path=sample_csv_file,
        target_table="STG_SALES",
        stage_name="RAW_STAGE",
        format_name="CSV_HEADER_FORMAT",
    )
    assert res["pipeline_status"] == "SUCCESS"
    assert res["upload"]["status"] == "UPLOADED"
    assert res["copy"]["status"] == "COMPLETED"
