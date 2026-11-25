"""
Data Quality Utilities Module.

Provides helper functions for data manipulation, formatting, statistical
calculations, and quality assessment tasks.
"""

from typing import List, Any, Union, Dict, Optional
import datetime
import pandas as pd
import numpy as np


def format_timestamp(dt: Optional[datetime.datetime] = None) -> str:
    """Format a datetime object as ISO 8601 string, defaulting to UTC now."""
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_date_parse(val: Any) -> Optional[datetime.datetime]:
    """Safely convert various input types into datetime objects."""
    if pd.isna(val) or val is None or val == "":
        return None
    if isinstance(val, (datetime.datetime, datetime.date)):
        return pd.to_datetime(val)
    try:
        return pd.to_datetime(val, errors="coerce")
    except Exception:
        return None


def compute_null_percentage(df: pd.DataFrame, column: str) -> float:
    """Calculate the percentage of null/missing values in a specific DataFrame column."""
    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame.")
    if len(df) == 0:
        return 0.0
    null_count = df[column].isna().sum()
    return float((null_count / len(df)) * 100.0)


def calculate_z_scores(series: pd.Series) -> pd.Series:
    """Compute Z-scores for a numerical pandas Series, handling zero standard deviation safely."""
    numeric_series = pd.to_numeric(series, errors="coerce")
    std = numeric_series.std()
    mean = numeric_series.mean()
    if pd.isna(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (numeric_series - mean) / std


def mask_to_indices(mask: pd.Series) -> List[int]:
    """Convert a boolean Series mask into list of integer row index positions."""
    return list(mask[mask].index)


def clean_column_names(columns: List[str]) -> List[str]:
    """Sanitize and standardize column names (lowercase, stripped, underscored)."""
    return [col.strip().lower().replace(" ", "_").replace("-", "_") for colcol in columns for col in [colcol]]
