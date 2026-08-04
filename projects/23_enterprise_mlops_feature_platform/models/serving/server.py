"""Model Serving - FastAPI-based model serving with A/B testing."""

import numpy as np
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from ..registry.registry import ModelRegistry, ModelVersion


# Prometheus metrics
prediction_counter = Counter(
    "model_predictions_total",
    "Total number of predictions",
    ["model_name", "version", "status"]
)
prediction_latency = Histogram(
    "model_prediction_latency_seconds",
    "Prediction latency in seconds",
    ["model_name", "version"]
)
prediction_confidence = Gauge(
    "model_prediction_confidence",
    "Average prediction confidence",
    ["model_name", "version"]
)
active_model_gauge = Gauge(
    "active_model_version",
    "Currently active model version",
    ["model_name"]
)


class ServingMode(str, Enum):
    """Model serving modes."""
    BATCH = "batch"
    ONLINE = "online"
    STREAMING = "streaming"


class PredictionRequest(BaseModel):
    """Prediction request."""
    entity_id: str
    features: dict[str, Any]
    model_name: str | None = None
    model_version: str | None = None


class PredictionResponse(BaseModel):
    """Prediction response."""
    prediction: Any
    confidence: float | None
    model_version: str
    timestamp: datetime


class ABTestConfig(BaseModel):
    """A/B test configuration."""
    champion_model: str
    challenger_model: str
    traffic_split: float = 0.5  # 50% traffic to challenger
    enabled: bool = True


class ModelServer:
    """FastAPI-based model serving with A/B testing."""
    
    def __init__(self, model_registry: ModelRegistry, serving_mode: ServingMode = ServingMode.ONLINE):
        """Initialize model server.
        
        Args:
            model_registry: Model registry instance
            serving_mode: Serving mode
        """
        self.model_registry = model_registry
        self.serving_mode = serving_mode
        self.loaded_models: dict[str, Any] = {}
        self.ab_test_configs: dict[str, ABTestConfig] = {}
        self.app = FastAPI(title="Model Serving API")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        app = self.app
        
        @app.get("/health")
        async def health():
            """Health check."""
            return {"status": "healthy", "mode": self.serving_mode.value}
        
        @app.post("/predict", response_model=PredictionResponse)
        async def predict(request: PredictionRequest):
            """Make prediction."""
            model_name = request.model_name or "default"
            
            # Determine which model to use
            model_version = self._resolve_model_version(model_name)
            
            # Load model
            model = self._load_model(model_version)
            
            # Make prediction
            try:
                with prediction_latency.labels(model_name, model_version.version).time():
                    prediction = model.predict(np.array([list(request.features.values())]))[0]
                    
                    # Get confidence if available
                    confidence = None
                    if hasattr(model, "predict_proba"):
                        proba = model.predict_proba(np.array([list(request.features.values())]))[0]
                        confidence = float(np.max(proba))
                    
                    # Record metrics
                    prediction_counter.labels(model_name, model_version.version, "success").inc()
                    prediction_confidence.labels(model_name, model_version.version).set(confidence or 0.5)
                    active_model_gauge.labels(model_name).set(float(model_version.version))
                    
                    return PredictionResponse(
                        prediction=prediction,
                        confidence=confidence,
                        model_version=model_version.version,
                        timestamp=datetime.now(),
                    )
            except Exception as e:
                prediction_counter.labels(model_name, model_version.version, "error").inc()
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/batch/predict")
        async def batch_predict(model_name: str, data: list[dict[str, Any]]):
            """Batch prediction."""
            model_version = self._resolve_model_version(model_name)
            model = self._load_model(model_version)
            
            predictions = []
            for record in data:
                prediction = model.predict(np.array([list(record.values())]))[0]
                predictions.append({
                    "entity_id": record.get("entity_id"),
                    "prediction": prediction,
                })
            
            return {
                "model_name": model_name,
                "model_version": model_version.version,
                "predictions": predictions,
            }
        
        @app.get("/models")
        async def list_models():
            """List all registered models."""
            return self.model_registry.list_models()
        
        @app.get("/models/{model_name}")
        async def get_model(model_name: str, version: str = None, stage: str = None):
            """Get model information."""
            model_stage = ModelStage(stage) if stage else None
            model = self.model_registry.get_model(model_name, version, model_stage)
            if not model:
                raise HTTPException(status_code=404, detail="Model not found")
            return model
        
        @app.post("/models/{model_name}/promote")
        async def promote_model(model_name: str, version: str, to_stage: str):
            """Promote model to stage."""
            stage = ModelStage(to_stage)
            
            if stage == ModelStage.STAGING:
                success = self.model_registry.promote_to_staging(model_name, version)
            elif stage == ModelStage.PRODUCTION:
                success = self.model_registry.promote_to_production(model_name, version)
            else:
                raise HTTPException(status_code=400, detail="Invalid stage")
            
            if not success:
                raise HTTPException(status_code=400, detail="Promotion failed")
            
            return {"message": f"Model promoted to {to_stage}"}
        
        @app.post("/ab-test/config")
        async def configure_ab_test(model_name: str, config: ABTestConfig):
            """Configure A/B test."""
            self.ab_test_configs[model_name] = config
            return {"message": "A/B test configured"}
    
    def _resolve_model_version(self, model_name: str) -> ModelVersion:
        """Resolve which model version to use.
        
        Args:
            model_name: Model name
            
        Returns:
            ModelVersion to use
        """
        # Check for A/B test
        if model_name in self.ab_test_configs:
            config = self.ab_test_configs[model_name]
            if config.enabled:
                # Simple random split
                import random
                if random.random() < config.traffic_split:
                    return self.model_registry.get_model(config.challenger_model)
                else:
                    return self.model_registry.get_model(config.champion_model)
        
        # Use production model
        model = self.model_registry.get_champion_model(model_name)
        if not model:
            # Fallback to staging
            model = self.model_registry.get_challenger_model(model_name)
        
        if not model:
            raise ValueError(f"No model found for {model_name}")
        
        return model
    
    def _load_model(self, model_version: ModelVersion) -> Any:
        """Load model from registry.
        
        Args:
            model_version: Model version
            
        Returns:
            Loaded model
        """
        # Check if already loaded
        cache_key = f"{model_version.name}:{model_version.version}"
        if cache_key in self.loaded_models:
            return self.loaded_models[cache_key]
        
        # Load model (simplified - in practice use mlflow.pyfunc.load_model)
        # model = mlflow.pyfunc.load_model(model_version.model_uri)
        model = None  # Placeholder
        
        # Cache model
        self.loaded_models[cache_key] = model
        
        return model
    
    def start_metrics_server(self, port: int = 8001) -> None:
        """Start Prometheus metrics server.
        
        Args:
            port: Metrics server port
        """
        start_http_server(port)


class BatchPredictor:
    """Batch prediction service."""
    
    def __init__(self, model_registry: ModelRegistry, spark: Any):
        """Initialize batch predictor.
        
        Args:
            model_registry: Model registry
            spark: Spark session
        """
        self.model_registry = model_registry
        self.spark = spark
    
    def predict(self, model_name: str, model_version: str, input_table: str, output_table: str) -> None:
        """Run batch predictions.
        
        Args:
            model_name: Model name
            model_version: Model version
            input_table: Input table
            output_table: Output table
        """
        # Load model
        model_version_obj = self.model_registry.get_model(model_name, model_version)
        if not model_version_obj:
            raise ValueError(f"Model {model_name}:{model_version} not found")
        
        # Read input data
        input_df = self.spark.read.table(input_table)
        
        # Load model and predict
        # model = mlflow.pyfunc.load_model(model_version_obj.model_uri)
        # predictions = model.predict(input_df.toPandas())
        
        # Write predictions
        # output_df = input_df.withColumn("prediction", predictions)
        # output_df.write.mode("overwrite").saveAsTable(output_table)
        pass


class StreamingPredictor:
    """Streaming prediction service with Kafka."""
    
    def __init__(self, model_registry: ModelRegistry, kafka_config: dict[str, Any]):
        """Initialize streaming predictor.
        
        Args:
            model_registry: Model registry
            kafka_config: Kafka configuration
        """
        self.model_registry = model_registry
        self.kafka_config = kafka_config
        self.model = None
    
    def start(self, input_topic: str, output_topic: str, model_name: str) -> None:
        """Start streaming predictions.
        
        Args:
            input_topic: Input Kafka topic
            output_topic: Output Kafka topic
            model_name: Model name
        """
        # Load production model
        model_version = self.model_registry.get_champion_model(model_name)
        if not model_version:
            raise ValueError(f"No production model found for {model_name}")
        
        # self.model = mlflow.pyfunc.load_model(model_version.model_uri)
        
        # Start Kafka consumer/producer
        # for message in kafka_consumer:
        #     features = extract_features(message)
        #     prediction = self.model.predict(features)
        #     kafka_producer.send(output_topic, prediction)
        pass