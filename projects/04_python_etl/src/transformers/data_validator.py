"""
Data Validator transformer for enforcing data quality business rules,
email validations, allowed status enumerations, and Dead Letter Queue (DLQ) routing.
"""

import re
from typing import Any, Dict, List, Tuple
import pandas as pd

from src.transformers.base_transformer import BaseTransformer, TransformationError
from src.utils.file_utils import safe_write_json


class DataValidator(BaseTransformer):
    """Transformer for validating records against business quality constraints."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Data Validator.

        Config Keys:
            email_regex (str): Regular expression pattern for valid emails.
            allowed_order_statuses (list): List of accepted status values.
            min_price (float): Minimum threshold for price/spent values.
            dlq_path (str, optional): Destination path for writing quarantined invalid records.
        """
        super().__init__(config)
        self.email_regex = config.get(
            "email_regex",
            r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        )
        self.allowed_statuses = config.get(
            "allowed_order_statuses",
            ["COMPLETED", "PENDING", "PROCESSING", "CANCELLED", "SHIPPED"]
        )
        self.min_price = config.get("min_price", 0.0)
        self.dlq_path = config.get("dlq_path", "output/dead_letter_queue.json")

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate DataFrame rows and split into valid records and rejected DLQ records.

        Args:
            df: Input DataFrame.

        Returns:
            pd.DataFrame: DataFrame containing only valid records.

        Raises:
            TransformationError: If validation fails critically.
        """
        if df.empty:
            return df.copy()

        try:
            valid_rows = []
            invalid_rows = []

            for idx, row in df.iterrows():
                is_valid, validation_reasons = self._validate_row(row)
                row_dict = row.to_dict()

                if is_valid:
                    valid_rows.append(row_dict)
                else:
                    row_dict["rejection_reasons"] = validation_reasons
                    invalid_rows.append(row_dict)

            valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

            if invalid_rows:
                self.logger.warning(
                    f"Validation filtered out {len(invalid_rows)} invalid rows out of {len(df)} total."
                )
                self._quarantine_records(invalid_rows)
            else:
                self.logger.info(f"Validation passed for all {len(df)} records.")

            return valid_df

        except Exception as e:
            msg = f"Data validation execution failed: {str(e)}"
            self.logger.error(msg)
            raise TransformationError(msg) from e

    def _validate_row(self, row: pd.Series) -> Tuple[bool, List[str]]:
        """Validate an individual row against business rules."""
        reasons: List[str] = []

        # 1. Validate Email regex if email column is present
        if "email" in row and pd.notna(row["email"]):
            email_str = str(row["email"]).strip()
            if not re.match(self.email_regex, email_str):
                reasons.append(f"Invalid email address format: '{email_str}'")

        # 2. Validate Order Status Enum if status column is present
        if "status" in row and pd.notna(row["status"]):
            status_str = str(row["status"]).strip().upper()
            if status_str not in [s.upper() for s in self.allowed_statuses]:
                reasons.append(f"Unrecognized status value: '{status_str}'")

        # 3. Validate non-negative financial values
        for price_col in ["price", "total_spent", "unit_price", "grand_total"]:
            if price_col in row and pd.notna(row[price_col]):
                try:
                    val = float(row[price_col])
                    if val < self.min_price:
                        reasons.append(f"Value in '{price_col}' ({val}) below minimum threshold ({self.min_price})")
                except (ValueError, TypeError):
                    reasons.append(f"Non-numeric value in column '{price_col}': {row[price_col]}")

        return (len(reasons) == 0, reasons)

    def _quarantine_records(self, invalid_records: List[Dict[str, Any]]) -> None:
        """Route rejected records to Dead Letter Queue (DLQ) JSON file."""
        if not self.dlq_path:
            return
        try:
            safe_write_json(invalid_records, self.dlq_path)
            self.logger.info(f"Quarantined {len(invalid_records)} invalid records to DLQ: {self.dlq_path}")
        except Exception as e:
            self.logger.error(f"Failed to quarantine records to DLQ: {str(e)}")
