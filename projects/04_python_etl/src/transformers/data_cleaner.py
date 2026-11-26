"""
Data Cleaner transformer for standardizing headers, trimming whitespace,
handling null values, and deduplicating rows.
"""

import re
from typing import Any, Dict, List, Optional
import pandas as pd

from src.transformers.base_transformer import BaseTransformer, TransformationError


class DataCleaner(BaseTransformer):
    """Transformer for data cleaning, sanitization, and deduplication operations."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Data Cleaner.

        Config Keys:
            trim_strings (bool): Strip leading/trailing whitespace from text (default: True).
            lowercase_headers (bool): Convert column headers to lowercase snake_case (default: True).
            drop_null_columns (list): Column names that cannot contain nulls.
            default_fill_values (dict): Mapping of column names to default values for missing data.
            deduplicate_subset (list, optional): Columns to check for duplicates.
        """
        super().__init__(config)
        self.trim_strings = config.get("trim_strings", True)
        self.lowercase_headers = config.get("lowercase_headers", True)
        self.drop_null_columns = config.get("drop_null_columns", [])
        self.default_fill_values = config.get("default_fill_values", {})
        self.deduplicate_subset = config.get("deduplicate_subset")

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Execute cleaning workflow on the input DataFrame.

        Args:
            df: Input raw DataFrame.

        Returns:
            pd.DataFrame: Cleaned dataset.

        Raises:
            TransformationError: If cleaning fails.
        """
        if df.empty:
            self.logger.warning("DataCleaner received empty DataFrame.")
            return df.copy()

        try:
            cleaned_df = df.copy()

            # 1. Standardize headers to snake_case
            if self.lowercase_headers:
                cleaned_df.columns = [
                    re.sub(r"[^\w]+", "_", col.strip().lower()).strip("_")
                    for col in cleaned_df.columns
                ]
                self.logger.debug("Standardized column headers to lowercase snake_case.")

            # 2. Trim whitespace from string cells
            if self.trim_strings:
                string_cols = cleaned_df.select_dtypes(include=["object", "string"]).columns
                for col in string_cols:
                    cleaned_df[col] = cleaned_df[col].apply(
                        lambda val: val.strip() if isinstance(val, str) else val
                    )
                self.logger.debug(f"Trimmed whitespace from {len(string_cols)} string columns.")

            # 3. Drop rows where key columns contain null values
            if self.drop_null_columns:
                target_null_cols = [c for c in self.drop_null_columns if c in cleaned_df.columns]
                if target_null_cols:
                    before_count = len(cleaned_df)
                    cleaned_df = cleaned_df.dropna(subset=target_null_cols)
                    after_count = len(cleaned_df)
                    dropped = before_count - after_count
                    if dropped > 0:
                        self.logger.info(f"Dropped {dropped} rows with nulls in key columns {target_null_cols}")

            # 4. Fill remaining null values using configured defaults
            if self.default_fill_values:
                for col, fill_val in self.default_fill_values.items():
                    if col in cleaned_df.columns:
                        cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                        self.logger.debug(f"Filled nulls in column '{col}' with '{fill_val}'")

            # 5. Deduplicate records
            before_dedup = len(cleaned_df)
            if self.deduplicate_subset:
                valid_subset = [c for c in self.deduplicate_subset if c in cleaned_df.columns]
                cleaned_df = cleaned_df.drop_duplicates(subset=valid_subset if valid_subset else None)
            else:
                hashable_cols = []
                for col in cleaned_df.columns:
                    sample_series = cleaned_df[col].dropna()
                    if not sample_series.empty:
                        first_val = sample_series.iloc[0]
                        if isinstance(first_val, (list, dict, set)):
                            continue
                    hashable_cols.append(col)
                cleaned_df = cleaned_df.drop_duplicates(subset=hashable_cols)
            dedup_dropped = before_dedup - len(cleaned_df)
            if dedup_dropped > 0:
                self.logger.info(f"Removed {dedup_dropped} duplicate rows.")

            self.logger.info(f"Data cleaning completed. Output shape: {cleaned_df.shape}")
            return cleaned_df

        except Exception as e:
            msg = f"Data cleaning failed: {str(e)}"
            self.logger.error(msg)
            raise TransformationError(msg) from e
