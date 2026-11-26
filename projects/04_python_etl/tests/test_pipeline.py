"""
Integration tests for the end-to-end ETL pipeline orchestrator.
"""

from pathlib import Path
import pytest
import yaml

from src.pipeline.pipeline_config import PipelineConfig, ConfigurationError
from src.pipeline.etl_pipeline import ETLPipeline, ETLPipelineExecutionError


def test_pipeline_config_loading(tmp_path: Path):
    """Test loading and validating YAML pipeline config."""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "pipeline": {"name": "test_pipeline", "log_level": "DEBUG"},
        "extractors": {},
        "transformers": {},
        "loaders": {}
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    cfg = PipelineConfig(config_file)
    assert cfg.pipeline_settings["name"] == "test_pipeline"


def test_pipeline_config_missing_sections(tmp_path: Path):
    """Test config validation raises ConfigurationError when missing sections."""
    config_file = tmp_path / "invalid_config.yaml"
    config_file.write_text("pipeline: {name: test}", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="missing required sections"):
        PipelineConfig(config_file)


def test_end_to_end_etl_pipeline(tmp_path: Path):
    """Test full ETL pipeline execution flow from extraction to loading."""
    # Create sample CSV and JSON files
    cust_file = tmp_path / "customers.csv"
    cust_file.write_text(
        "customer_id,first_name,last_name,email,country,signup_date,status,total_spent\n"
        "CUST-001,John,Doe,john@example.com,USA,2023-01-15,active,1250.50\n"
        "CUST-002,Jane,Smith,jane@example.org,Canada,2023-02-20,active,3400.00\n",
        encoding="utf-8"
    )

    orders_file = tmp_path / "orders.json"
    orders_file.write_text(
        '[{"order_id": "ORD-1", "customer_id": "CUST-001", "status": "COMPLETED", "items": [{"product_id": "P1", "quantity": 1, "unit_price": 50.0}]}]',
        encoding="utf-8"
    )

    output_parquet = tmp_path / "out_customers.parquet"
    output_csv = tmp_path / "out_orders.csv"
    output_db = tmp_path / "warehouse.db"

    config_dict = {
        "pipeline": {
            "name": "integration_test_pipeline",
            "log_level": "DEBUG",
            "log_file": str(tmp_path / "test.log")
        },
        "extractors": {
            "customers_csv": {"type": "csv", "path": str(cust_file)},
            "orders_json": {"type": "json", "path": str(orders_file)}
        },
        "transformers": {
            "cleaning": {"lowercase_headers": True, "trim_strings": True},
            "enrichment": {"base_currency": "USD", "tax_rate": 0.08},
            "validation": {
                "allowed_order_statuses": ["COMPLETED", "ACTIVE"],
                "dlq_path": str(tmp_path / "dlq.json")
            }
        },
        "loaders": {
            "processed_customers_parquet": {"type": "parquet", "path": str(output_parquet)},
            "processed_orders_csv": {"type": "csv", "path": str(output_csv)},
            "sqlite_db": {
                "type": "database",
                "connection_string": f"sqlite:///{output_db}",
                "tables": {"customers": "dim_customers", "orders": "fact_orders"}
            }
        }
    }

    config_path = tmp_path / "pipeline_config.yaml"
    config_path.write_text(yaml.dump(config_dict), encoding="utf-8")

    cfg = PipelineConfig(config_path)
    pipeline = ETLPipeline(cfg)
    report = pipeline.run()

    assert report["status"] == "SUCCESS"
    assert report["records_extracted"] == 3  # 2 customers + 1 order
    assert report["records_transformed"] == 3
    assert output_parquet.exists()
    assert output_csv.exists()
    assert output_db.exists()
