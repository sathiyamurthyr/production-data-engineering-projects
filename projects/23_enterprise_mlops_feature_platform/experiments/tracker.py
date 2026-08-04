"""Experiment Tracker - MLflow-based experiment tracking."""

from datetime import datetime
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient
from pydantic import BaseModel


class ExperimentRun(BaseModel):
    """MLflow experiment run."""
    run_id: str
    experiment_name: str
    run_name: str
    status: str
    start_time: datetime
    end_time: datetime | None
    
    # Parameters
    hyperparameters: dict[str, Any]
    
    # Metrics
    metrics: dict[str, float]
    
    # Artifacts
    artifacts: list[str]
    
    # Tags
    tags: dict[str, str]


class ExperimentTracker:
    """MLflow-based experiment tracking with enterprise features."""
    
    def __init__(self, tracking_uri: str = "http://localhost:5000", experiment_name: str = "default"):
        """Initialize experiment tracker.
        
        Args:
            tracking_uri: MLflow tracking server URI
            experiment_name: Default experiment name
        """
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        self.experiment_name = experiment_name
        
        # Create or get experiment
        self.experiment_id = self._get_or_create_experiment(experiment_name)
    
    def _get_or_create_experiment(self, experiment_name: str) -> str:
        """Get or create experiment.
        
        Args:
            experiment_name: Experiment name
            
        Returns:
            Experiment ID
        """
        experiment = self.client.get_experiment_by_name(experiment_name)
        if experiment:
            return experiment.experiment_id
        
        return self.client.create_experiment(
            name=experiment_name,
            artifact_location=f"s3://mlflow-artifacts/{experiment_name}",
        )
    
    def start_run(self, run_name: str, tags: dict[str, str] = None) -> str:
        """Start a new experiment run.
        
        Args:
            run_name: Name for the run
            tags: Run tags
            
        Returns:
            Run ID
        """
        # Set experiment
        mlflow.set_experiment(self.experiment_name)
        
        # Start run
        run = mlflow.start_run(run_name=run_name, tags=tags or {})
        
        # Log system info
        mlflow.log_params({
            "python_version": "3.13",
            "platform": "databricks",
            "cluster_id": "cluster-123",
        })
        
        return run.info.run_id
    
    def end_run(self, run_id: str, status: str = "FINISHED") -> None:
        """End experiment run.
        
        Args:
            run_id: Run ID
            status: Run status
        """
        try:
            run = self.client.get_run(run_id)
            mlflow.end_run(run_id=run_id, status=status)
        except Exception as e:
            print(f"Error ending run: {e}")
    
    def log_parameters(self, run_id: str, parameters: dict[str, Any]) -> None:
        """Log hyperparameters.
        
        Args:
            run_id: Run ID
            parameters: Hyperparameters
        """
        try:
            with mlflow.start_run(run_id=run_id):
                mlflow.log_params(parameters)
        except Exception as e:
            print(f"Error logging parameters: {e}")
    
    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int = None) -> None:
        """Log metrics.
        
        Args:
            run_id: Run ID
            metrics: Metrics dictionary
            step: Step number (optional)
        """
        try:
            with mlflow.start_run(run_id=run_id):
                for key, value in metrics.items():
                    mlflow.log_metric(key, value, step=step)
        except Exception as e:
            print(f"Error logging metrics: {e}")
    
    def log_artifact(self, run_id: str, local_path: str, artifact_path: str = None) -> None:
        """Log artifact.
        
        Args:
            run_id: Run ID
            local_path: Local file path
            artifact_path: Artifact path in MLflow
        """
        try:
            with mlflow.start_run(run_id=run_id):
                mlflow.log_artifact(local_path, artifact_path)
        except Exception as e:
            print(f"Error logging artifact: {e}")
    
    def log_model(self, run_id: str, model: Any, artifact_path: str = "model") -> str:
        """Log model.
        
        Args:
            run_id: Run ID
            model: Model object
            artifact_path: Artifact path
            
        Returns:
            Model URI
        """
        try:
            with mlflow.start_run(run_id=run_id):
                model_uri = mlflow.sklearn.log_model(
                    model,
                    artifact_path,
                    registered_model_name=None,
                )
                return model_uri
        except Exception as e:
            print(f"Error logging model: {e}")
            return ""
    
    def get_run(self, run_id: str) -> ExperimentRun | None:
        """Get experiment run.
        
        Args:
            run_id: Run ID
            
        Returns:
            ExperimentRun object or None
        """
        try:
            run = self.client.get_run(run_id)
            
            return ExperimentRun(
                run_id=run.info.run_id,
                experiment_name=self.experiment_name,
                run_name=run.info.run_name,
                status=run.info.status,
                start_time=datetime.fromtimestamp(run.info.start_time / 1000),
                end_time=datetime.fromtimestamp(run.info.end_time / 1000) if run.info.end_time else None,
                hyperparameters=run.data.params,
                metrics=run.data.metrics,
                artifacts=[artifact.path for artifact in self.client.list_artifacts(run_id)],
                tags=run.data.tags,
            )
        except Exception as e:
            print(f"Error getting run: {e}")
            return None
    
    def list_runs(self, experiment_id: str = None, filter_string: str = None) -> list[ExperimentRun]:
        """List experiment runs.
        
        Args:
            experiment_id: Experiment ID (optional)
            filter_string: Filter string (optional)
            
        Returns:
            List of ExperimentRun objects
        """
        try:
            experiment_id = experiment_id or self.experiment_id
            
            runs = self.client.search_runs(
                experiment_ids=[experiment_id],
                filter_string=filter_string,
                order_by=["start_time DESC"],
            )
            
            return [
                ExperimentRun(
                    run_id=run.info.run_id,
                    experiment_name=self.experiment_name,
                    run_name=run.info.run_name,
                    status=run.info.status,
                    start_time=datetime.fromtimestamp(run.info.start_time / 1000),
                    end_time=datetime.fromtimestamp(run.info.end_time / 1000) if run.info.end_time else None,
                    hyperparameters=run.data.params,
                    metrics=run.data.metrics,
                    artifacts=[artifact.path for artifact in self.client.list_artifacts(run.info.run_id)],
                    tags=run.data.tags,
                )
                for run in runs
            ]
        except Exception as e:
            print(f"Error listing runs: {e}")
            return []
    
    def compare_runs(self, run_ids: list[str]) -> dict[str, Any]:
        """Compare multiple runs.
        
        Args:
            run_ids: List of run IDs
            
        Returns:
            Comparison results
        """
        try:
            runs = [self.get_run(run_id) for run_id in run_ids]
            
            comparison = {
                "runs": [],
                "metrics_comparison": {},
                "parameters_comparison": {},
            }
            
            for run in runs:
                if not run:
                    continue
                
                comparison["runs"].append({
                    "run_id": run.run_id,
                    "run_name": run.run_name,
                    "status": run.status,
                    "start_time": run.start_time,
                })
                
                # Compare metrics
                for metric, value in run.metrics.items():
                    if metric not in comparison["metrics_comparison"]:
                        comparison["metrics_comparison"][metric] = {}
                    comparison["metrics_comparison"][metric][run.run_id] = value
                
                # Compare parameters
                for param, value in run.hyperparameters.items():
                    if param not in comparison["parameters_comparison"]:
                        comparison["parameters_comparison"][param] = {}
                    comparison["parameters_comparison"][param][run.run_id] = value
            
            return comparison
        except Exception as e:
            print(f"Error comparing runs: {e}")
            return {}
    
    def get_best_run(self, metric_name: str, mode: str = "max") -> ExperimentRun | None:
        """Get best run based on metric.
        
        Args:
            metric_name: Metric name
            mode: 'max' or 'min'
            
        Returns:
            Best ExperimentRun or None
        """
        try:
            # Filter runs with the metric
            filter_string = f"metrics.{metric_name} != ''"
            runs = self.list_runs(filter_string=filter_string)
            
            if not runs:
                return None
            
            # Sort by metric
            sorted_runs = sorted(
                runs,
                key=lambda r: r.metrics.get(metric_name, float('-inf') if mode == "max" else float('inf')),
                reverse=(mode == "max")
            )
            
            return sorted_runs[0] if sorted_runs else None
        except Exception as e:
            print(f"Error getting best run: {e}")
            return None
    
    def delete_run(self, run_id: str) -> bool:
        """Delete experiment run.
        
        Args:
            run_id: Run ID
            
        Returns:
            True if successful
        """
        try:
            self.client.delete_run(run_id)
            return True
        except Exception as e:
            print(f"Error deleting run: {e}")
            return False


class ExperimentComparator:
    """Compare and analyze experiment runs."""
    
    def __init__(self, tracker: ExperimentTracker):
        """Initialize experiment comparator.
        
        Args:
            tracker: ExperimentTracker instance
        """
        self.tracker = tracker
    
    def compare_hyperparameters(self, run_ids: list[str]) -> dict[str, Any]:
        """Compare hyperparameters across runs.
        
        Args:
            run_ids: List of run IDs
            
        Returns:
            Hyperparameter comparison
        """
        comparison = {}
        
        for run_id in run_ids:
            run = self.tracker.get_run(run_id)
            if not run:
                continue
            
            for param, value in run.hyperparameters.items():
                if param not in comparison:
                    comparison[param] = {}
                comparison[param][run_id] = value
        
        return comparison
    
    def compare_metrics(self, run_ids: list[str]) -> dict[str, Any]:
        """Compare metrics across runs.
        
        Args:
            run_ids: List of run IDs
            
        Returns:
            Metrics comparison
        """
        comparison = {}
        
        for run_id in run_ids:
            run = self.tracker.get_run(run_id)
            if not run:
                continue
            
            for metric, value in run.metrics.items():
                if metric not in comparison:
                    comparison[metric] = {}
                comparison[metric][run_id] = value
        
        return comparison
    
    def find_optimal_hyperparameters(self, run_ids: list[str], metric_name: str, mode: str = "max") -> dict[str, Any]:
        """Find optimal hyperparameters from runs.
        
        Args:
            run_ids: List of run IDs
            metric_name: Metric to optimize
            mode: 'max' or 'min'
            
        Returns:
            Optimal hyperparameters
        """
        best_run = self.tracker.get_best_run(metric_name, mode)
        if not best_run:
            return {}
        
        return {
            "run_id": best_run.run_id,
            "metric_value": best_run.metrics.get(metric_name),
            "hyperparameters": best_run.hyperparameters,
        }
    
    def get_metric_trajectory(self, run_id: str, metric_name: str) -> list[dict[str, Any]]:
        """Get metric trajectory over steps.
        
        Args:
            run_id: Run ID
            metric_name: Metric name
            
        Returns:
            List of metric values over time
        """
        # This would query MLflow for metric history
        # Simplified for now
        run = self.tracker.get_run(run_id)
        if not run:
            return []
        
        return [
            {
                "step": i,
                "value": run.metrics.get(metric_name),
            }
            for i in range(len(run.metrics))
        ]