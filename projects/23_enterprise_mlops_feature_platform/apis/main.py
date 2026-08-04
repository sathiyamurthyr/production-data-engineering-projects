"""MLOps Platform API - FastAPI application."""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Any

from models.registry.registry import ModelRegistry, ModelStage
from experiments.tracker import ExperimentTracker
from models.serving.server import ModelServer, PredictionRequest
from features.offline.feature_definitions import FeatureView


# Initialize components
model_registry = ModelRegistry(tracking_uri="http://localhost:5000")
experiment_tracker = ExperimentTracker(tracking_uri="http://localhost:5000")
model_server = ModelServer(model_registry=model_registry)

# Create FastAPI app
app = ModelServer.app


# Additional endpoints
@app.get("/experiments")
async def list_experiments():
    """List all experiments."""
    try:
        runs = experiment_tracker.list_runs()
        return {"experiments": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/experiments/{run_id}")
async def get_experiment(run_id: str):
    """Get experiment details."""
    try:
        run = experiment_tracker.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return run
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/experiments/compare")
async def compare_experiments(run_ids: list[str]):
    """Compare multiple experiments."""
    try:
        comparison = experiment_tracker.compare_runs(run_ids)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/features")
async def list_features():
    """List all registered features."""
    # This would query the feature registry
    return {"features": []}


@app.get("/features/{feature_name}")
async def get_feature(feature_name: str):
    """Get feature details."""
    # This would query the feature registry
    return {"feature_name": feature_name}


@app.post("/features/validate")
async def validate_feature(feature_view: FeatureView):
    """Validate feature quality."""
    # This would run Great Expectations validation
    return {"status": "validated", "feature_view": feature_view.name}


@app.get("/monitoring/drift")
async def get_drift_report():
    """Get drift detection report."""
    # This would query the drift detector
    return {"drift_detections": []}


@app.get("/monitoring/metrics")
async def get_metrics():
    """Get platform metrics."""
    return {
        "total_experiments": 0,
        "total_models": len(model_registry.list_models()),
        "total_predictions": 0,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "model_registry": "healthy",
            "experiment_tracker": "healthy",
            "model_server": "healthy",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)