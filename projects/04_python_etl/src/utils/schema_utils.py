"""
Schema enforcement and validation utilities for DataFrame operations.

Provides type checking, schema drift detection, missing column detection,
and robust data type casting.
"""

import logging
from typing import Dict, List, Tuple, Any
import pandas as pd

logger = logging.getLogger("etl_pipeline.utils.schema")


class SchemaValidationError(Exception):
    """Raised when data schema fails validation rules."""
    pass


def validate_schema(
    df: pd.DataFrame,
    expected_schema: Dict[str, str],
    allow_extra_columns: bool = True
) -> Tuple[bool, List[str]]:
    """
    Validate that a DataFrame contains expected columns and basic types.

    Args:
        df: DataFrame to validate.
        expected_schema: Dict mapping column name to expected pandas/python type string
                         (e.g., {'customer_id': 'object', 'total_spent': 'float64'}).
        allow_extra_columns: Whether extra columns present in df cause validation failure.

    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
    """
    errors: List[str] = []

    # Check missing columns
    df_cols = set(df.columns)
    req_cols = set(expected_schema.keys())
    missing_cols = req_cols - df_cols

    if missing_cols:
        errors.append(f"Missing required columns: {sorted(list(missing_cols))}")

    # Check unexpected columns if extra columns not allowed
    if not allow_extra_columns:
        extra_cols = df_cols - req_cols
        if extra_cols:
            errors.append(f"Unexpected extra columns found: {sorted(list(extra_cols))}")

    # Check basic types for existing columns
    for col, expected_type in expected_schema.items():
        if col in df.columns:
            actual_type = str(df[col].dtype)
            # Basic checks e.g. int, float, object/string
            if "int" in expected_type and "int" not in actual_type:
                errors.append(f"Column '{col}' expected type '{expected_type}', got '{actual_type}'")
            elif "float" in expected_type and "float" not in actual_type and "int" not in actual_type:
                errors.append(f"Column '{col}' expected type '{expected_type}', got '{actual_type}'")

    is_valid = len(errors) == 0
    if not is_valid:
        logger.warning(f"Schema validation failed with {len(errors)} issues.")
    else:
        logger.info("Schema validation passed successfully.")

    return is_valid, errors


def cast_dataframe_schema(
    df: pd.DataFrame,
    schema_types: Dict[str, str],
    strict: bool = False
) -> pd.DataFrame:
    """
    Cast DataFrame columns to target data types safely.

    Args:
        df: Input DataFrame.
        schema_types: Mapping of column names to numpy/pandas dtype strings.
        strict: If True, raises exception on cast failure; if False, coercing handles errors.

    Returns:
        pd.DataFrame: DataFrame with updated column types.

    Raises:
        SchemaValidationError: If strict is True and casting fails.
    """
    df_copy = df.copy()
    for col, target_type in schema_types.items():
        if col not in df_copy.columns:
            logger.warning(f"Cannot cast missing column '{col}'")
            continue

        try:
            if target_type in ["int", "int64", "Int64"]:
                df_copy[col] = pd.to_numeric(df_copy[col], errors="coerce" if not strict else "raise").astype("Int64")
            elif target_type in ["float", "float64"]:
                df_copy[col] = pd.to_numeric(df_copy[col], errors="coerce" if not strict else "raise").astype("float64")
            elif target_type in ["str", "string", "object"]:
                df_copy[col] = df_copy[col].astype(str)
            elif target_type in ["datetime", "datetime64[ns]"]:
                df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce" if not strict else "raise")
            elif target_type == "bool":
                df_copy[col] = df_copy[col].astype(bool)
            else:
                df_copy[col] = df_copy[col].astype(target_type)
            logger.debug(f"Cast column '{col}' to '{target_type}'")
        except Exception as e:
            msg = f"Failed casting column '{col}' to '{target_type}': {str(e)}"
            logger.error(msg)
            if strict:
                raise SchemaValidationError(msg) from e

    return df_copy
