"""Drift Detection - Data drift, concept drift, and prediction drift monitoring."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from scipy import stats
from pydantic import BaseModel


class DriftType(str, Enum):
    """Types of drift."""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    FEATURE_DRIFT = "feature_drift"


class DriftResult(BaseModel):
    """Drift detection result."""
    drift_type: DriftType
    feature_name: str
    drift_score: float
    threshold: float
    is_drifted: bool
    p_value: float | None
    timestamp: datetime
    details: dict[str, Any]


class DriftDetector:
    """Detect data drift, concept drift, and prediction drift."""
    
    def __init__(self, threshold: float = 0.05):
        """Initialize drift detector.
        
        Args:
            threshold: P-value threshold for drift detection
        """
        self.threshold = threshold
        self.reference_data: dict[str, np.ndarray] = {}
        self.drift_history: list[DriftResult] = []
    
    def set_reference_data(self, feature_name: str, data: np.ndarray) -> None:
        """Set reference (baseline) data for a feature.
        
        Args:
            feature_name: Feature name
            data: Reference data array
        """
        self.reference_data[feature_name] = data
    
    def detect_data_drift(self, feature_name: str, current_data: np.ndarray) -> DriftResult:
        """Detect data drift using statistical tests.
        
        Args:
            feature_name: Feature name
            current_data: Current data array
            
        Returns:
            DriftResult
        """
        if feature_name not in self.reference_data:
            raise ValueError(f"No reference data for feature: {feature_name}")
        
        reference = self.reference_data[feature_name]
        
        # Kolmogorov-Smirnov test
        ks_statistic, p_value = stats.ks_2samp(reference, current_data)
        
        # Population Stability Index (PSI)
        psi = self._calculate_psi(reference, current_data)
        
        # Determine if drift detected
        is_drifted = p_value < self.threshold or psi > 0.2
        
        result = DriftResult(
            drift_type=DriftType.DATA_DRIFT,
            feature_name=feature_name,
            drift_score=ks_statistic,
            threshold=self.threshold,
            is_drifted=is_drifted,
            p_value=p_value,
            timestamp=datetime.now(),
            details={
                "psi": psi,
                "ks_statistic": ks_statistic,
                "reference_mean": float(np.mean(reference)),
                "current_mean": float(np.mean(current_data)),
                "reference_std": float(np.std(reference)),
                "current_std": float(np.std(current_data)),
            },
        )
        
        self.drift_history.append(result)
        return result
    
    def detect_concept_drift(
        self,
        y_true_reference: np.ndarray,
        y_true_current: np.ndarray,
        y_pred_reference: np.ndarray,
        y_pred_current: np.ndarray,
    ) -> DriftResult:
        """Detect concept drift by comparing model performance.
        
        Args:
            y_true_reference: True labels for reference period
            y_true_current: True labels for current period
            y_pred_reference: Predictions for reference period
            y_pred_current: Predictions for current period
            
        Returns:
            DriftResult
        """
        from sklearn.metrics import accuracy_score, f1_score
        
        # Calculate performance metrics
        reference_accuracy = accuracy_score(y_true_reference, y_pred_reference)
        current_accuracy = accuracy_score(y_true_current, y_pred_current)
        
        reference_f1 = f1_score(y_true_reference, y_pred_reference, average="weighted")
        current_f1 = f1_score(y_true_current, y_pred_current, average="weighted")
        
        # Calculate performance drop
        accuracy_drop = reference_accuracy - current_accuracy
        f1_drop = reference_f1 - current_f1
        
        # Determine if drift detected
        is_drifted = accuracy_drop > 0.05 or f1_drop > 0.05
        
        result = DriftResult(
            drift_type=DriftType.CONCEPT_DRIFT,
            feature_name="model_performance",
            drift_score=accuracy_drop,
            threshold=0.05,
            is_drifted=is_drifted,
            p_value=None,
            timestamp=datetime.now(),
            details={
                "reference_accuracy": reference_accuracy,
                "current_accuracy": current_accuracy,
                "accuracy_drop": accuracy_drop,
                "reference_f1": reference_f1,
                "current_f1": current_f1,
                "f1_drop": f1_drop,
            },
        )
        
        self.drift_history.append(result)
        return result
    
    def detect_prediction_drift(
        self,
        reference_predictions: np.ndarray,
        current_predictions: np.ndarray,
    ) -> DriftResult:
        """Detect prediction distribution drift.
        
        Args:
            reference_predictions: Predictions for reference period
            current_predictions: Predictions for current period
            
        Returns:
            DriftResult
        """
        # Chi-squared test for categorical predictions
        if len(np.unique(reference_predictions)) <= 10:
            # Categorical
            chi2, p_value = stats.chi2_contingency([
                np.bincount(reference_predictions),
                np.bincount(current_predictions),
            ])[:2]
            
            is_drifted = p_value < self.threshold
            drift_score = chi2
        else:
            # Continuous
            ks_statistic, p_value = stats.ks_2samp(reference_predictions, current_predictions)
            is_drifted = p_value < self.threshold
            drift_score = ks_statistic
        
        result = DriftResult(
            drift_type=DriftType.PREDICTION_DRIFT,
            feature_name="predictions",
            drift_score=drift_score,
            threshold=self.threshold,
            is_drifted=is_drifted,
            p_value=p_value,
            timestamp=datetime.now(),
            details={
                "reference_mean": float(np.mean(reference_predictions)),
                "current_mean": float(np.mean(current_predictions)),
                "reference_std": float(np.std(reference_predictions)),
                "current_std": float(np.std(current_predictions)),
            },
        )
        
        self.drift_history.append(result)
        return result
    
    def detect_feature_drift(self, feature_name: str, current_data: np.ndarray) -> DriftResult:
        """Detect drift for a specific feature.
        
        Args:
            feature_name: Feature name
            current_data: Current data array
            
        Returns:
            DriftResult
        """
        return self.detect_data_drift(feature_name, current_data)
    
    def get_drift_report(self) -> dict[str, Any]:
        """Generate drift report.
        
        Returns:
            Drift report
        """
        if not self.drift_history:
            return {"message": "No drift detections"}
        
        recent_drifts = [d for d in self.drift_history if (datetime.now() - d.timestamp).days < 7]
        
        return {
            "total_detections": len(self.drift_history),
            "recent_detections": len(recent_drifts),
            "drifted_features": list(set(d.feature_name for d in recent_drifts if d.is_drifted)),
            "drift_by_type": {
                drift_type.value: len([d for d in recent_drifts if d.drift_type == drift_type])
                for drift_type in DriftType
            },
        }
    
    def _calculate_psi(self, reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
        """Calculate Population Stability Index (PSI).
        
        Args:
            reference: Reference data
            current: Current data
            bins: Number of bins
            
        Returns:
            PSI score
        """
        # Create bins based on reference data
        bin_edges = np.histogram_bin_edges(reference, bins=bins)
        
        # Calculate distributions
        reference_hist, _ = np.histogram(reference, bins=bin_edges)
        current_hist, _ = np.histogram(current, bins=bin_edges)
        
        # Normalize to percentages
        reference_pct = reference_hist / len(reference)
        current_pct = current_hist / len(current)
        
        # Add small epsilon to avoid division by zero
        epsilon = 1e-10
        reference_pct = np.maximum(reference_pct, epsilon)
        current_pct = np.maximum(current_pct, epsilon)
        
        # Calculate PSI
        psi = np.sum((current_pct - reference_pct) * np.log(current_pct / reference_pct))
        
        return float(psi)