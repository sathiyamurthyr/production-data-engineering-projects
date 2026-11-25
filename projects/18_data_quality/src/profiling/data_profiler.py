"""
Data Profiler Module.

Provides comprehensive column-level profiling for pandas DataFrames, including
data types, completeness, cardinality, statistical summaries, and memory footprint.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class DataProfiler:
    """
    Automated profiler for computing dataset-wide and column-level metrics.
    """

    def __init__(self, dataset_name: str = "dataset"):
        self.dataset_name = dataset_name

    def profile(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate complete statistical profile for a DataFrame.

        Args:
            df: Input pandas DataFrame.

        Returns:
            Dictionary containing overall summary and column-level profile dictionaries.
        """
        total_rows = len(df)
        total_cols = len(df.columns)
        memory_bytes = int(df.memory_usage(deep=True).sum())

        column_profiles = {}
        for col in df.columns:
            column_profiles[col] = self._profile_column(df[col], total_rows)

        return {
            "dataset_name": self.dataset_name,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "memory_footprint_bytes": memory_bytes,
            "memory_footprint_mb": round(memory_bytes / (1024 * 1024), 2),
            "columns": column_profiles,
        }

    def _profile_column(self, series: pd.Series, total_rows: int) -> Dict[str, Any]:
        """Generate profile metrics for a single pandas Series."""
        null_count = int(series.isna().sum())
        null_pct = (null_count / total_rows * 100.0) if total_rows > 0 else 0.0
        distinct_count = int(series.nunique(dropna=True))
        distinct_pct = (distinct_count / total_rows * 100.0) if total_rows > 0 else 0.0

        profile = {
            "dtype": str(series.dtype),
            "null_count": null_count,
            "null_percentage": round(null_pct, 2),
            "distinct_count": distinct_count,
            "distinct_percentage": round(distinct_pct, 2),
            "is_unique": distinct_count == (total_rows - null_count),
        }

        # Numeric column statistics
        if pd.api.types.is_numeric_dtype(series.dtype) and not pd.api.types.is_bool_dtype(series.dtype):
            clean_series = series.dropna()
            if len(clean_series) > 0:
                profile.update({
                    "min": float(clean_series.min()) if not np.isnan(clean_series.min()) else None,
                    "max": float(clean_series.max()) if not np.isnan(clean_series.max()) else None,
                    "mean": float(clean_series.mean()) if not np.isnan(clean_series.mean()) else None,
                    "std": float(clean_series.std()) if not np.isnan(clean_series.std()) else None,
                    "median": float(clean_series.median()) if not np.isnan(clean_series.median()) else None,
                    "p25": float(clean_series.quantile(0.25)) if not np.isnan(clean_series.quantile(0.25)) else None,
                    "p75": float(clean_series.quantile(0.75)) if not np.isnan(clean_series.quantile(0.75)) else None,
                    "zeros_count": int((clean_series == 0).sum()),
                })
        else:
            # Categorical / string top values
            top_values = series.value_counts(dropna=True).head(5).to_dict()
            profile["top_frequent_values"] = {str(k): int(v) for k, v in top_values.items()}

        return profile
