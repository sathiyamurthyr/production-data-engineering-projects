import pandas as pd
from typing import Dict, Any, Optional

class SchemaProfiler:
    """
    Analyzes the structure and schema of a DataFrame, detects drift against a baseline schema,
    and profiles nullability and uniqueness.
    """

    def __init__(self, baseline_schema: Optional[Dict[str, str]] = None):
        self.baseline_schema = baseline_schema or {}

    @staticmethod
    def profile(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generates schema profile for the DataFrame.
        
        Args:
            df (pd.DataFrame): Input DataFrame.
            
        Returns:
            Dict[str, Any]: Schema profile details.
        """
        num_rows = len(df)
        columns_profile = {}

        for col in df.columns:
            series = df[col]
            null_count = int(series.isna().sum())
            null_pct = round((null_count / num_rows) * 100, 2) if num_rows > 0 else 0.0
            
            # Uniqueness
            non_null_series = series.dropna()
            unique_count = int(non_null_series.nunique())
            total_non_null = len(non_null_series)
            uniqueness_pct = round((unique_count / total_non_null) * 100, 2) if total_non_null > 0 else 0.0

            columns_profile[col] = {
                "inferred_type": str(series.dtype),
                "null_count": null_count,
                "null_percentage": null_pct,
                "unique_count": unique_count,
                "uniqueness_percentage": uniqueness_pct,
                "is_nullable": null_count > 0,
                "is_unique": unique_count == num_rows and num_rows > 0
            }

        return {
            "row_count": num_rows,
            "column_count": len(df.columns),
            "columns": columns_profile
        }

    def detect_drift(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compares the schema of the input DataFrame against the configured baseline schema.
        
        Args:
            df (pd.DataFrame): The DataFrame to check for schema drift.
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - has_drift (bool): True if there is schema drift.
                - added_columns (List[str]): Columns present in df but not in baseline.
                - missing_columns (List[str]): Columns present in baseline but not in df.
                - type_mismatches (Dict[str, Dict[str, str]]): Columns with different data types.
        """
        current_schema = {col: str(df[col].dtype) for col in df.columns}
        
        added_columns = [col for col in current_schema if col not in self.baseline_schema]
        missing_columns = [col for col in self.baseline_schema if col not in current_schema]
        
        type_mismatches = {}
        for col in self.baseline_schema:
            if col in current_schema:
                baseline_type = self.baseline_schema[col]
                current_type = current_schema[col]
                # Compare simplified types (e.g. integer vs float etc. or exact string)
                # For robust comparison, we check if exact string matches, or normalize common names
                if baseline_type != current_type:
                    # Check if they are compatible numeric types to reduce false alarms in production
                    numeric_types = ["int64", "float64", "int32", "float32"]
                    if not (baseline_type in numeric_types and current_type in numeric_types):
                        type_mismatches[col] = {
                            "expected": baseline_type,
                            "actual": current_type
                        }
                        
        has_drift = len(added_columns) > 0 or len(missing_columns) > 0 or len(type_mismatches) > 0
        
        return {
            "has_drift": has_drift,
            "added_columns": added_columns,
            "missing_columns": missing_columns,
            "type_mismatches": type_mismatches
        }
