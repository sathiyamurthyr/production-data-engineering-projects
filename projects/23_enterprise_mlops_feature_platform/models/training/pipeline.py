"""Training Pipeline - End-to-end ML training pipeline."""

from datetime import datetime
from typing import Any

import mlflow
import numpy as np
from pyspark.sql import DataFrame, SparkSession
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from ..registry.registry import ModelRegistry, ModelVersion
from ...experiments.tracker import ExperimentTracker


class TrainingPipeline:
    """End-to-end training pipeline."""
    
    def __init__(
        self,
        spark: SparkSession,
        model_registry: ModelRegistry,
        experiment_tracker: ExperimentTracker,
        config: dict[str, Any],
    ):
        """Initialize training pipeline.
        
        Args:
            spark: PySpark session
            model_registry: Model registry
            experiment_tracker: Experiment tracker
            config: Pipeline configuration
        """
        self.spark = spark
        self.model_registry = model_registry
        self.experiment_tracker = experiment_tracker
        self.config = config
    
    def run(self) -> dict[str, Any]:
        """Run the training pipeline.
        
        Returns:
            Training results
        """
        # 1. Extract features
        print("Extracting features...")
        features_df = self._extract_features()
        
        # 2. Prepare data
        print("Preparing data...")
        X_train, X_val, y_train, y_val = self._prepare_data(features_df)
        
        # 3. Train model
        print("Training model...")
        model = self._train_model(X_train, y_train)
        
        # 4. Validate model
        print("Validating model...")
        validation_results = self._validate_model(model, X_val, y_val)
        
        # 5. Log experiment
        print("Logging experiment...")
        run_id = self._log_experiment(model, validation_results)
        
        # 6. Register model
        print("Registering model...")
        model_version = self._register_model(model, run_id, validation_results)
        
        return {
            "run_id": run_id,
            "model_version": model_version.version,
            "validation_results": validation_results,
            "status": "completed",
        }
    
    def _extract_features(self) -> DataFrame:
        """Extract features from feature store.
        
        Returns:
            Features DataFrame
        """
        # Read from feature store
        feature_table = self.config.get("feature_table", "gold.features")
        df = self.spark.read.table(feature_table)
        
        return df
    
    def _prepare_data(self, features_df: DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for training.
        
        Args:
            features_df: Features DataFrame
            
        Returns:
            X_train, X_val, y_train, y_val
        """
        # Convert to pandas
        pdf = features_df.toPandas()
        
        # Separate features and target
        target_col = self.config.get("target", "label")
        feature_cols = [c for c in pdf.columns if c != target_col and c != "entity_id"]
        
        X = pdf[feature_cols].values
        y = pdf[target_col].values
        
        # Train/validation split
        test_size = self.config.get("validation_split", 0.2)
        random_state = self.config.get("random_state", 42)
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        return X_train, X_val, y_train, y_val
    
    def _train_model(self, X_train: np.ndarray, y_train: np.ndarray) -> Any:
        """Train model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            
        Returns:
            Trained model
        """
        algorithm = self.config.get("algorithm", "xgboost")
        hyperparameters = self.config.get("hyperparameters", {})
        
        if algorithm == "xgboost":
            import xgboost as xgb
            model = xgb.XGBClassifier(**hyperparameters)
            model.fit(X_train, y_train)
        elif algorithm == "random_forest":
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(**hyperparameters)
            model.fit(X_train, y_train)
        elif algorithm == "logistic_regression":
            from sklearn.linear_model import LogisticRegression
            model = LogisticRegression(**hyperparameters)
            model.fit(X_train, y_train)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        return model
    
    def _validate_model(self, model: Any, X_val: np.ndarray, y_val: np.ndarray) -> dict[str, float]:
        """Validate model.
        
        Args:
            model: Trained model
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Validation metrics
        """
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val) if hasattr(model, "predict_proba") else None
        
        metrics = {
            "accuracy": accuracy_score(y_val, y_pred),
            "precision": precision_score(y_val, y_pred, average="weighted"),
            "recall": recall_score(y_val, y_pred, average="weighted"),
            "f1": f1_score(y_val, y_pred, average="weighted"),
        }
        
        if y_pred_proba is not None and len(np.unique(y_val)) == 2:
            metrics["auc"] = roc_auc_score(y_val, y_pred_proba[:, 1])
        
        return metrics
    
    def _log_experiment(self, model: Any, validation_results: dict[str, float]) -> str:
        """Log experiment to MLflow.
        
        Args:
            model: Trained model
            validation_results: Validation metrics
            
        Returns:
            Run ID
        """
        # Start experiment
        experiment_name = self.config.get("experiment_name", "default")
        run_name = self.config.get("run_name", f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        self.experiment_tracker.experiment_name = experiment_name
        run_id = self.experiment_tracker.start_run(run_name=run_name, tags={
            "algorithm": self.config.get("algorithm", "unknown"),
            "pipeline": "training",
        })
        
        # Log hyperparameters
        self.experiment_tracker.log_parameters(run_id, self.config.get("hyperparameters", {}))
        
        # Log metrics
        self.experiment_tracker.log_metrics(run_id, validation_results)
        
        # Log model
        self.experiment_tracker.log_model(run_id, model, "model")
        
        # End run
        self.experiment_tracker.end_run(run_id, status="FINISHED")
        
        return run_id
    
    def _register_model(self, model: Any, run_id: str, validation_results: dict[str, float]) -> ModelVersion:
        """Register model in registry.
        
        Args:
            model: Trained model
            run_id: MLflow run ID
            validation_results: Validation metrics
            
        Returns:
            ModelVersion object
        """
        model_name = self.config.get("model_name", "default")
        model_uri = f"runs:/{run_id}/model"
        
        # Register model
        model_version = self.model_registry.register_model(
            model_name=model_name,
            model_uri=model_uri,
            run_id=run_id,
            description=f"Model trained on {datetime.now().strftime('%Y-%m-%d')}",
            tags={
                "algorithm": self.config.get("algorithm", "unknown"),
                "validation_auc": str(validation_results.get("auc", 0)),
            },
        )
        
        return model_version


class HyperparameterTuner:
    """Hyperparameter tuning with Optuna."""
    
    def __init__(self, spark: SparkSession, experiment_tracker: ExperimentTracker):
        """Initialize hyperparameter tuner.
        
        Args:
            spark: PySpark session
            experiment_tracker: Experiment tracker
        """
        self.spark = spark
        self.experiment_tracker = experiment_tracker
    
    def optimize(self, config: dict[str, Any], n_trials: int = 100) -> dict[str, Any]:
        """Optimize hyperparameters.
        
        Args:
            config: Pipeline configuration
            n_trials: Number of trials
            
        Returns:
            Best hyperparameters
        """
        import optuna
        
        def objective(trial):
            # Define hyperparameter search space
            hyperparameters = {
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "gamma": trial.suggest_float("gamma", 0, 0.5),
            }
            
            # Update config
            trial_config = config.copy()
            trial_config["hyperparameters"] = hyperparameters
            
            # Train and evaluate
            pipeline = TrainingPipeline(
                spark=self.spark,
                model_registry=None,  # Not needed for tuning
                experiment_tracker=self.experiment_tracker,
                config=trial_config,
            )
            
            # Extract and prepare data
            features_df = pipeline._extract_features()
            X_train, X_val, y_train, y_val = pipeline._prepare_data(features_df)
            
            # Train model
            model = pipeline._train_model(X_train, y_train)
            
            # Validate
            metrics = pipeline._validate_model(model, X_val, y_val)
            
            # Log trial
            trial.set_user_attr("metrics", metrics)
            
            return metrics.get("auc", 0)
        
        # Create study
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)
        
        return {
            "best_params": study.best_params,
            "best_value": study.best_value,
            "best_trial": study.best_trial.number,
        }