"""
Statistical Profiler Module.

Performs advanced statistical distribution profiling including skewness, kurtosis,
inter-column correlation matrices, and distribution metrics.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from scipy import stats


class StatisticalProfiler:
    """
    Advanced statistical profiler for numerical distribution metrics and correlation discovery.
    """

    def __init__(self, dataset_name: str = "dataset"):
        self.dataset_name = dataset_name

    def profile_distributions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute skewness, kurtosis, and distribution characteristics for all numeric columns.
        """
        numeric_df = df.select_dtypes(include=[np.number])
        col_stats = {}

        for col in numeric_df.columns:
            series = numeric_df[col].dropna()
            if len(series) < 3:
                continue

            skew_val = float(series.skew())
            kurt_val = float(series.kurtosis())

            col_stats[col] = {
                "count": int(len(series)),
                "mean": float(series.mean()),
                "variance": float(series.var()),
                "skewness": round(skew_val, 4),
                "kurtosis": round(kurt_val, 4),
                "is_highly_skewed": abs(skew_val) > 1.0,
                "is_heavy_tailed": kurt_val > 3.0,
            }

        correlation_matrix = {}
        if len(numeric_df.columns) > 1:
            corr_df = numeric_df.corr().round(4)
            correlation_matrix = corr_df.to_dict()

        return {
            "dataset_name": self.dataset_name,
            "numeric_columns_count": len(numeric_df.columns),
            "column_distributions": col_stats,
            "correlation_matrix": correlation_matrix,
        }
