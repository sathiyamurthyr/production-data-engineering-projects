import os
import sys
import pytest
from pyspark.sql import SparkSession

# Set project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.glue_context import get_glue_context
from src.s3_integration import S3DataConnector
from src.dynamic_frame_ops import resolve_choices, drop_null_fields, select_fields, unnest_nested_fields
from src.data_quality_glue import GlueDataQualityEvaluator

@pytest.fixture(scope="module")
def spark_env():
    """Initializes a local PySpark/Mock Glue environment for testing."""
    sc, glue_context, spark_session = get_glue_context()
    yield glue_context, spark_session

def test_s3_read_local_fallback(spark_env):
    """Verifies that reading local/mock S3 data resolves and reads correctly."""
    glue_context, spark_session = spark_env
    connector = S3DataConnector(glue_context)
    
    # Read the sample csv using our connector
    # S3DataConnector translates "s3://" to local file "sample-data/sample_s3_data.csv" for local runs
    dyf = connector.read_from_s3(
        s3_path="s3://data-engineering-diaries-glue-demo/raw/sales/",
        file_format="csv"
    )
    
    assert dyf is not None
    assert dyf.count() == 10
    
    # Verify columns exist
    df = dyf.toDF()
    assert "order_id" in df.columns
    assert "revenue" in df.columns

def test_dynamic_frame_resolve_choices(spark_env):
    """Tests the resolveChoice schema casting mapping."""
    glue_context, spark_session = spark_env
    connector = S3DataConnector(glue_context)
    dyf = connector.read_from_s3("s3://data-engineering-diaries-glue-demo/raw/sales/", "csv")
    
    # Before casting, columns are strings
    df_raw = dyf.toDF()
    assert dict(df_raw.dtypes)["revenue"] == "string"
    
    # Perform choices cast
    schema_specs = [
        ("revenue", "cast:double"),
        ("discount", "cast:double")
    ]
    casted_dyf = resolve_choices(dyf, specs=schema_specs)
    df_casted = casted_dyf.toDF()
    
    assert dict(df_casted.dtypes)["revenue"] == "double"
    assert dict(df_casted.dtypes)["discount"] == "double"

def test_dynamic_frame_drop_null_fields(spark_env):
    """Tests dropNullFields wrapper."""
    glue_context, spark_session = spark_env
    
    # Create test data with entirely null columns
    schema = ["id", "val", "all_null"]
    data = [
        (1, "A", None),
        (2, "B", None),
        (3, None, None)
    ]
    df = spark_session.createDataFrame(data, schema)
    
    from src.glue_context import MockDynamicFrame
    dyf = MockDynamicFrame(df)
    
    cleaned_dyf = drop_null_fields(dyf)
    cleaned_df = cleaned_dyf.toDF()
    
    # Columns containing ONLY null values should be dropped
    assert "all_null" not in cleaned_df.columns
    # val should be kept because it has at least one non-null value ('A', 'B')
    assert "val" in cleaned_df.columns

def test_dynamic_frame_select_fields(spark_env):
    """Tests selectFields projection wrapper."""
    glue_context, spark_session = spark_env
    connector = S3DataConnector(glue_context)
    dyf = connector.read_from_s3("s3://data-engineering-diaries-glue-demo/raw/sales/", "csv")
    
    pruned_dyf = select_fields(dyf, ["order_id", "revenue"])
    pruned_df = pruned_dyf.toDF()
    
    assert len(pruned_df.columns) == 2
    assert "order_id" in pruned_df.columns
    assert "revenue" in pruned_df.columns
    assert "status" not in pruned_df.columns

def test_data_quality_evaluation(spark_env):
    """Tests the DQDL ruleset evaluation simulation."""
    glue_context, spark_session = spark_env
    connector = S3DataConnector(glue_context)
    dyf = connector.read_from_s3("s3://data-engineering-diaries-glue-demo/raw/sales/", "csv")
    
    # Test valid specs
    rules = [
        "RowCount > 0",
        "ColumnCount == 8",
        "ColumnExists \"order_id\"",
        "IsComplete \"order_id\""
    ]
    evaluator = GlueDataQualityEvaluator("test_rules", rules)
    passed, report, _ = evaluator.evaluate(dyf)
    
    assert passed is True
    assert len(report) == 4
    for r in report:
        assert r["Status"] == "PASSED"

    # Test failing specs
    failing_rules = [
        "RowCount > 100", # we have only 10 rows
        "ColumnExists \"non_existent_column\""
    ]
    failing_evaluator = GlueDataQualityEvaluator("fail_rules", failing_rules)
    fail_passed, fail_report, _ = failing_evaluator.evaluate(dyf)
    
    assert fail_passed is False
    assert fail_report[0]["Status"] == "FAILED"
    assert fail_report[1]["Status"] == "FAILED"
