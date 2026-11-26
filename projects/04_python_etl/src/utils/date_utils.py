"""
Date and time parsing utilities for ETL pipeline data normalization.

Provides ISO 8601 standard datetime conversions, epoch time transformations,
and DataFrame date column standardizations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Union
import pandas as pd

logger = logging.getLogger("etl_pipeline.utils.date")


class DateParsingError(Exception):
    """Custom exception raised when date parsing fails."""
    pass


def parse_iso_datetime(date_str: str) -> datetime:
    """
    Parse ISO-8601 string or standard formatted date into UTC datetime object.

    Args:
        date_str: String formatted date (e.g. '2023-09-01T10:15:30Z' or '2023-01-15').

    Returns:
        datetime: UTC-aware or naive datetime object.

    Raises:
        DateParsingError: If formatting is invalid.
    """
    if not isinstance(date_str, str) or not date_str.strip():
        raise DateParsingError(f"Invalid date input string: {date_str}")

    cleaned = date_str.strip()
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            if fmt.endswith("Z"):
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    raise DateParsingError(f"Could not parse date string '{date_str}' against known formats.")


def format_iso_datetime(dt: Optional[datetime] = None) -> str:
    """
    Format a datetime object into standard ISO-8601 string format (UTC).

    Args:
        dt: Datetime instance. If None, current UTC timestamp is used.

    Returns:
        str: ISO formatted string e.g. '2023-09-01T10:15:30Z'.
    """
    target_dt = dt or datetime.now(timezone.utc)
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=timezone.utc)
    else:
        target_dt = target_dt.astimezone(timezone.utc)
    return target_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_dates(
    df: pd.DataFrame,
    date_columns: list[str],
    output_format: str = "%Y-%m-%d"
) -> pd.DataFrame:
    """
    Standardize multiple date columns in a Pandas DataFrame to a uniform string format.

    Args:
        df: Input pandas DataFrame.
        date_columns: List of column names containing dates.
        output_format: Desired datetime strftime format.

    Returns:
        pd.DataFrame: DataFrame with normalized date columns.
    """
    df_copy = df.copy()
    for col in date_columns:
        if col in df_copy.columns:
            try:
                converted = pd.to_datetime(df_copy[col], errors="coerce")
                df_copy[col] = converted.dt.strftime(output_format)
                logger.debug(f"Normalized date column '{col}' to format '{output_format}'")
            except Exception as e:
                logger.warning(f"Failed standardizing date column '{col}': {str(e)}")
        else:
            logger.warning(f"Date column '{col}' missing from DataFrame.")
    return df_copy
