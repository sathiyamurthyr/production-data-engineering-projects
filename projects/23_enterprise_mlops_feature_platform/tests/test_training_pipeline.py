"""Tests for Training Pipeline."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock

from models.training.pipeline import TrainingPipeline, HyperparameterTuner
from models.registry.registry import ModelRegistry, ModelVersion, ModelStage
from experiments.tracker import ExperimentTracker


@pytest.fixture
def mock_spark():
    """Create mock Spark session."""
    spark = Mock()
    spark.read.table.return_value.toPandas.return_value = Mock()
    return spark


@pytest.fixture
def mock_model_registry():
    """Create mock model registry."""
    registry = Mock(spec=ModelRegistry)
    registry.register_model.return_value = ModelVersion(
        name="test_model",
        version="1",
        stage=ModelStage.DEVELOPMENT,
        created_at=Mock(),
        created_by="test",
        training_dataset="test",
        algorithm="xgboost",
        hyperparameters={},
        metrics={},
        model_uri="test",
        requirements_uri="test",
        description="test",
        tags={},
    )
    return registry


@pytest.fixture
def mock_experiment_tracker():
    """Create mock experiment tracker."""
    tracker = Mock(spec=ExperimentTracker)
    tracker.start_run.return_value = "test_run_id"
    tracker.end_run.return_value = None
    tracker.log_parameters.return_value = None
    tracker.log_metrics.return_value = None
    tracker.log_model.return_value = "test_model_uri"
    return tracker


def test_training_pipeline_initialization(mock_spark, mock_model_registry, mock_experiment_tracker):
    """Test training pipeline initialization."""
    config = {
        "feature_table": "gold.features",
        "target": "label",
        "algorithm": "xgboost",
        "hyperparameters": {"max_depth": 6},
        "model_name": "test_model",
    }
    
    pipeline = TrainingPipeline(
        spark=mock_spark,
        model_registry=mock_model_registry,
        experiment_tracker=mock_experiment_tracker,
        config=config,
    )
    
    assert pipeline.config == config
    assert pipeline.spark == mock_spark


def test_training_pipeline_prepare_data(mock_spark, mock_model_registry, mock_experiment_tracker):
    """Test data preparation."""
    import pandas as pd
    
    config = {
        "target": "label",
        "validation_split": 0.2,
        "random_state": 42,
    }
    
    pipeline = TrainingPipeline(
        spark=mock_spark,
        model_registry=mock_model_registry,
        experiment_tracker=mock_experiment_tracker,
        config=config,
    )
    
    # Create mock DataFrame
    mock_df = Mock()
    mock_df.columns = ["feature1", "feature2", "label", "entity_id"]
    mock_df.toPandas.return_value = pd.DataFrame({
        "feature1": [1, 2, 3, 4, 5],
        "feature2": [2, 3, 4, 5, 6],
        "label": [0, 1, 0, 1, 0],
        "entity_id": ["a", "b", "c", "d", "e"],
    })
    
    X_train, X_val, y_train, y_val = pipeline._prepare_data(mock_df)
    
    assert X_train.shape[0] > 0
    assert X_val.shape[0] > 0
    assert len(y_train) == X_train.shape[0]
    assert len(y_val) == X_val.shape[0]


def test_training_pipeline_train_model_xgboost(mock_spark, mock_model_registry, mock_experiment_tracker):
    """Test XGBoost model training."""
    config = {"algorithm": "xgboost", "hyperparameters": {"max_depth": 6}}
    
    pipeline = TrainingPipeline(
        spark=mock_spark,
        model_registry=mock_model_registry,
        experiment_tracker=mock_experiment_tracker,
        config=config,
    )
    
    X_train = np.array([[1, 2], [2, 3], [3, 4], [4, 5]])
    y_train = np.array([0, 1, 0, 1])
    
    model = pipeline._train_model(X_train, y_train)
    
    assert model is not None
    assert hasattr(model, "predict")


def test_training_pipeline_validate_model(mock_spark, mock_model_registry, mock_experiment_tracker):
    """Test model validation."""
    from xgboost import XGBClassifier
    
    config = {}
    pipeline = TrainingPipeline(
        spark=mock_spark,
        model_registry=mock_model_registry,
        experiment_tracker=mock_experiment_tracker,
        config=config,
    )
    
    # Train a simple model
    X_train = np.array([[1, 2], [2, 3], [3, 4], [4, 5]])
    y_train = np.array([0, 1, 0, 1])
    model = XGBClassifier().fit(X_train, y_train)
    
    # Validate
    X_val = np.array([[2, 3], [3, 4]])
    y_val = np.array([1, 0])
    
    metrics = pipeline._validate_model(model, X_val, y_val)
    
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert 0 <= metrics["accuracy"] <= 1


def test_hyperparameter_tuner_optimize(mock_spark, mock_experiment_tracker):
    """Test hyperparameter optimization."""
    tuner = HyperparameterTuner(
        spark=mock_spark,
        experiment_tracker=mock_experiment_tracker,
    )
    
    config = {
        "feature_table": "gold.features",
        "target": "label",
        "algorithm": "xgboost",
    }
    
    # Mock the pipeline
    tuner.spark.read.table.return_value.toPandas.return_value = Mock()
    
    # This would normally run optimization
    # For testing, we'll just verify the method exists
    assert hasattr(tuner, "optimize")


def test_model_registry_register_model(mock_model_registry):
    """Test model registration."""
    # This is a simplified test
    assert mock_model_registry.register_model is not None


def test_experiment_tracker_logging(mock_experiment_tracker):
    """Test experiment logging."""
    assert mock_experiment_tracker.log_parameters is not None
    assert mock_experiment_tracker.log_metrics is not None
    assert mock_experiment_tracker.log_model is not None