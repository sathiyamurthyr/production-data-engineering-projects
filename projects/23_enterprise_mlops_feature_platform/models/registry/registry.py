"""Model Registry - MLflow-based model registry with promotion workflows."""

from datetime import datetime
from enum import Enum
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient
from pydantic import BaseModel


class ModelStage(str, Enum):
    """Model deployment stages."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelVersion(BaseModel):
    """Model version information."""
    name: str
    version: str
    stage: ModelStage
    created_at: datetime
    created_by: str
    
    # Training info
    training_dataset: str
    algorithm: str
    hyperparameters: dict[str, Any]
    
    # Metrics
    metrics: dict[str, float]
    
    # Artifacts
    model_uri: str
    requirements_uri: str
    
    # Metadata
    description: str
    tags: dict[str, str]


class ModelRegistry:
    """MLflow-based model registry with enterprise workflows."""
    
    def __init__(self, tracking_uri: str = "http://localhost:5000"):
        """Initialize model registry.
        
        Args:
            tracking_uri: MLflow tracking server URI
        """
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        self.stages = [stage.value for stage in ModelStage]
    
    def register_model(
        self,
        model_name: str,
        model_uri: str,
        run_id: str,
        description: str = "",
        tags: dict[str, str] = None,
    ) -> ModelVersion:
        """Register a model in the registry.
        
        Args:
            model_name: Name of the model
            model_uri: MLflow model URI
            run_id: MLflow run ID
            description: Model description
            tags: Model tags
            
        Returns:
            ModelVersion object
        """
        # Register model
        result = mlflow.register_model(model_uri, model_name)
        
        # Get run info
        run = self.client.get_run(run_id)
        
        # Update model version
        version = result.version
        self.client.update_model_version(
            name=model_name,
            version=version,
            description=description or f"Model {model_name} version {version}",
        )
        
        # Add tags
        if tags:
            for key, value in tags.items():
                self.client.set_model_version_tag(model_name, version, key, value)
        
        # Create ModelVersion object
        model_version = ModelVersion(
            name=model_name,
            version=version,
            stage=ModelStage.DEVELOPMENT,
            created_at=datetime.now(),
            created_by=run.info.user_id,
            training_dataset=run.data.params.get("training_dataset", ""),
            algorithm=run.data.params.get("algorithm", ""),
            hyperparameters=run.data.params,
            metrics=run.data.metrics,
            model_uri=model_uri,
            requirements_uri=f"{model_uri}/requirements.txt",
            description=description,
            tags=tags or {},
        )
        
        return model_version
    
    def promote_to_staging(self, model_name: str, version: str) -> bool:
        """Promote model to staging.
        
        Args:
            model_name: Model name
            version: Model version
            
        Returns:
            True if successful
        """
        try:
            # Validate model before promotion
            validation_result = self._validate_model(model_name, version)
            if not validation_result["passed"]:
                raise ValueError(f"Model validation failed: {validation_result['reason']}")
            
            # Transition to staging
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=ModelStage.STAGING.value,
                archive_existing_versions=True,
            )
            
            return True
        except Exception as e:
            print(f"Error promoting model to staging: {e}")
            return False
    
    def promote_to_production(self, model_name: str, version: str) -> bool:
        """Promote model to production.
        
        Args:
            model_name: Model name
            version: Model version
            
        Returns:
            True if successful
        """
        try:
            # Validate model
            validation_result = self._validate_for_production(model_name, version)
            if not validation_result["passed"]:
                raise ValueError(f"Production validation failed: {validation_result['reason']}")
            
            # Transition to production
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=ModelStage.PRODUCTION.value,
                archive_existing_versions=True,
            )
            
            return True
        except Exception as e:
            print(f"Error promoting model to production: {e}")
            return False
    
    def rollback(self, model_name: str, target_version: str) -> bool:
        """Rollback to previous model version.
        
        Args:
            model_name: Model name
            target_version: Version to rollback to
            
        Returns:
            True if successful
        """
        try:
            # Archive current production version
            production_versions = self.client.get_latest_versions(
                model_name, stages=[ModelStage.PRODUCTION.value]
            )
            
            for version in production_versions:
                self.client.transition_model_version_stage(
                    name=model_name,
                    version=version.version,
                    stage=ModelStage.ARCHIVED.value,
                )
            
            # Promote target version to production
            self.client.transition_model_version_stage(
                name=model_name,
                version=target_version,
                stage=ModelStage.PRODUCTION.value,
            )
            
            return True
        except Exception as e:
            print(f"Error rolling back model: {e}")
            return False
    
    def get_model(self, model_name: str, version: str = None, stage: ModelStage = None) -> ModelVersion | None:
        """Get model version.
        
        Args:
            model_name: Model name
            version: Specific version (optional)
            stage: Filter by stage (optional)
            
        Returns:
            ModelVersion object or None
        """
        try:
            if version:
                # Get specific version
                mv = self.client.get_model_version(model_name, version)
            elif stage:
                # Get latest version in stage
                versions = self.client.get_latest_versions(model_name, stages=[stage.value])
                if versions:
                    mv = versions[0]
                else:
                    return None
            else:
                # Get production version
                versions = self.client.get_latest_versions(model_name, stages=[ModelStage.PRODUCTION.value])
                if versions:
                    mv = versions[0]
                else:
                    return None
            
            # Get run info
            run = self.client.get_run(mv.run_id)
            
            return ModelVersion(
                name=mv.name,
                version=mv.version,
                stage=ModelStage(mv.current_stage),
                created_at=datetime.fromtimestamp(mv.creation_timestamp / 1000),
                created_by=run.info.user_id,
                training_dataset=run.data.params.get("training_dataset", ""),
                algorithm=run.data.params.get("algorithm", ""),
                hyperparameters=run.data.params,
                metrics=run.data.metrics,
                model_uri=mv.source,
                requirements_uri=f"{mv.source}/requirements.txt",
                description=mv.description or "",
                tags=mv.tags,
            )
        except Exception as e:
            print(f"Error getting model: {e}")
            return None
    
    def list_models(self, stage: ModelStage = None) -> list[dict[str, Any]]:
        """List all registered models.
        
        Args:
            stage: Filter by stage (optional)
            
        Returns:
            List of model information
        """
        models = []
        for model in self.client.search_registered_models():
            for version in model.latest_versions:
                if stage is None or version.current_stage == stage.value:
                    models.append({
                        "name": model.name,
                        "version": version.version,
                        "stage": version.current_stage,
                        "created_at": datetime.fromtimestamp(version.creation_timestamp / 1000),
                        "metrics": self._get_model_metrics(model.name, version.version),
                    })
        return models
    
    def _validate_model(self, model_name: str, version: str) -> dict[str, Any]:
        """Validate model before promotion to staging.
        
        Args:
            model_name: Model name
            version: Model version
            
        Returns:
            Validation result
        """
        try:
            # Get model version
            mv = self.client.get_model_version(model_name, version)
            run = self.client.get_run(mv.run_id)
            
            # Check minimum metrics
            required_metrics = {
                "auc": 0.80,
                "precision": 0.75,
                "recall": 0.70,
            }
            
            for metric, threshold in required_metrics.items():
                if metric not in run.data.metrics:
                    return {"passed": False, "reason": f"Missing metric: {metric}"}
                
                if run.data.metrics[metric] < threshold:
                    return {"passed": False, "reason": f"Metric {metric} below threshold: {run.data.metrics[metric]} < {threshold}"}
            
            return {"passed": True}
        except Exception as e:
            return {"passed": False, "reason": str(e)}
    
    def _validate_for_production(self, model_name: str, version: str) -> dict[str, Any]:
        """Validate model before promotion to production.
        
        Args:
            model_name: Model name
            version: Model version
            
        Returns:
            Validation result
        """
        # Staging validation + additional checks
        staging_validation = self._validate_model(model_name, version)
        if not staging_validation["passed"]:
            return staging_validation
        
        try:
            # Get model version
            mv = self.client.get_model_version(model_name, version)
            run = self.client.get_run(mv.run_id)
            
            # Check for A/B test results
            if "ab_test_result" not in run.data.metrics:
                return {"passed": False, "reason": "Missing A/B test results"}
            
            # Check if model outperformed champion
            ab_test_result = run.data.metrics["ab_test_result"]
            if ab_test_result < 0.0:  # Model lost to champion
                return {"passed": False, "reason": "Model did not outperform champion in A/B test"}
            
            return {"passed": True}
        except Exception as e:
            return {"passed": False, "reason": str(e)}
    
    def _get_model_metrics(self, model_name: str, version: str) -> dict[str, float]:
        """Get model metrics.
        
        Args:
            model_name: Model name
            version: Model version
            
        Returns:
            Model metrics
        """
        try:
            mv = self.client.get_model_version(model_name, version)
            run = self.client.get_run(mv.run_id)
            return run.data.metrics
        except Exception:
            return {}
    
    def get_champion_model(self, model_name: str) -> ModelVersion | None:
        """Get current champion (production) model.
        
        Args:
            model_name: Model name
            
        Returns:
            ModelVersion object or None
        """
        return self.get_model(model_name, stage=ModelStage.PRODUCTION)
    
    def get_challenger_model(self, model_name: str) -> ModelVersion | None:
        """Get current challenger (staging) model.
        
        Args:
            model_name: Model name
            
        Returns:
            ModelVersion object or None
        """
        return self.get_model(model_name, stage=ModelStage.STAGING)