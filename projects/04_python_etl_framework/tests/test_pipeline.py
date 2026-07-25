"""
ETL Framework Tests

Production tests for the Python ETL framework.
"""

import pytest
from unittest.mock import Mock, MagicMock
import tempfile
import os

from etl_framework.core.pipeline import Pipeline, ExecutionContext, PipelineStatus
from etl_framework.extract.csv_reader import CSVReader, CSVConfig
from etl_framework.transform.cleaner import DataCleaner, CleanerConfig
from etl_framework.load.db_loader import DatabaseLoader, DBConfig
from etl_framework.validation.validator import DataValidator, ValidationRule, SchemaValidator
from etl_framework.monitoring.metrics import MetricsCollector, PipelineMetrics


class TestCSVReader:
    """Tests for CSV extractor."""
    
    def test_extract_returns_records(self, tmp_path):
        """Test CSV extraction returns expected records."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name,value\n1,Test,100\n2,Demo,200\n")
        
        reader = CSVReader(config=CSVConfig(path=str(csv_file)))
        records = reader.extract()
        
        assert len(records) == 2
        assert records[0]["id"] == "1"
        assert records[0]["name"] == "Test"
    
    def test_extract_handles_empty_strings(self, tmp_path):
        """Test empty strings converted to None."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name\n1,\n2,Test\n")
        
        reader = CSVReader(config=CSVConfig(path=str(csv_file)))
        records = reader.extract()
        
        assert records[0]["name"] is None


class TestPipeline:
    """Tests for pipeline orchestration."""
    
    def test_pipeline_runs_successfully(self):
        """Test full pipeline execution."""
        mock_extractor = Mock()
        mock_extractor.extract.return_value = [
            {"id": "1", "name": "Test"},
            {"id": "2", "name": "Demo"},
        ]
        
        mock_loader = Mock()
        mock_loader.load.return_value = 2
        
        pipeline = Pipeline(
            name="test_pipeline",
            extractor=mock_extractor,
            loader=mock_loader,
        )
        
        context = pipeline.run()
        
        assert context.status == PipelineStatus.SUCCESS
        assert context.records_processed == 2
        mock_extractor.extract.assert_called_once()
        mock_loader.load.assert_called_once()


class TestDataValidator:
    """Tests for data validation."""
    
    def test_validate_required_field(self):
        """Test required field validation."""
        validator = DataValidator(rules=[
            ValidationRule(column="email", rule_type="required")
        ])
        
        records = [{"email": None, "name": "Test"}]
        result = validator.validate(records)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_email_format(self):
        """Test email format validation."""
        validator = DataValidator(rules=[
            ValidationRule(column="email", rule_type="email")
        ])
        
        records = [{"email": "invalid-email", "name": "Test"}]
        result = validator.validate(records)
        
        assert result.is_valid is False


class TestMetricsCollector:
    """Tests for metrics collection."""
    
    def test_metrics_collection(self):
        """Test metrics are collected correctly."""
        collector = MetricsCollector()
        
        metric = collector.start_pipeline("test")
        collector.record_success("test", 100)
        metric.stop()
        
        metrics = collector.get_metrics("test")
        assert metrics["records_processed"] == 100
        assert metrics["duration_seconds"] > 0
        assert "throughput_rps" in metrics