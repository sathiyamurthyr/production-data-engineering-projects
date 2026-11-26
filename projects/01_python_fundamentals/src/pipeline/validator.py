"""
Data Validation Engine.
Performs schema validation, null checks, and isolates invalid records into quarantine CSV.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("pipeline.validator")

class DataValidator:
    """Validates raw transaction dictionaries and quarentines bad records."""

    def __init__(self, quarantine_path: Path) -> None:
        self.quarantine_path = quarantine_path

    def validate_transactions(self, raw_records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        valid_records: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []

        for record in raw_records:
            txn_id = record.get("transaction_id")
            amount_raw = record.get("amount")
            status = record.get("status")

            error_reasons = []

            if not txn_id or str(txn_id).strip() == "":
                error_reasons.append("Missing transaction_id")
            
            try:
                amount = float(amount_raw) if amount_raw is not None else -1.0
                if amount < 0:
                    error_reasons.append(f"Invalid or negative amount: {amount_raw}")
            except (ValueError, TypeError):
                error_reasons.append(f"Non-numeric amount: {amount_raw}")

            if status in ["FAILED", "INVALID"]:
                error_reasons.append(f"Transaction status is {status}")

            if error_reasons:
                invalid_records.append({
                    "transaction_id": txn_id or "UNKNOWN",
                    "error_reason": "; ".join(error_reasons),
                    "raw_data": str(record)
                })
            else:
                valid_records.append(record)

        if invalid_records:
            self._quarantine_records(invalid_records)

        logger.info(f"Validation finished: {len(valid_records)} valid, {len(invalid_records)} quarantined.")
        return valid_records, invalid_records

    def _quarantine_records(self, invalid_records: List[Dict[str, Any]]) -> None:
        self.quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self.quarantine_path.exists()
        
        with open(self.quarantine_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["transaction_id", "error_reason", "raw_data"])
            if not file_exists:
                writer.writeheader()
            for rec in invalid_records:
                writer.writerow(rec)
