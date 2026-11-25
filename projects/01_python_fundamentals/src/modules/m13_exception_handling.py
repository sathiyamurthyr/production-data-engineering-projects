"""
================================================================================
MODULE 13: Exception Handling & Resilience
================================================================================
1. EXPLANATION:
Robust exception handling prevents single corrupted rows from crashing multi-hour data pipeline runs.
Custom exceptions define enterprise failure taxonomy.

2. BUSINESS USE CASE:
Catch data parsing errors, log corrupted records to dead-letter queues (DLQ), and continue batch execution.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("m13_exceptions")

class DataValidationError(Exception):
    """Custom exception raised when record fails critical data contract."""
    pass

def parse_record_safely(record: Dict[str, Any]) -> Dict[str, Any]:
    """Parse record and raise DataValidationError if critical keys are missing."""
    if "id" not in record:
        raise DataValidationError("Record missing mandatory key 'id'")
    try:
        amount = float(record["amount"])
    except (ValueError, KeyError, TypeError) as e:
        raise DataValidationError(f"Invalid amount value in record {record}: {e}")
    return {"id": record["id"], "amount": amount}

if __name__ == "__main__":
    sample = {"amount": "invalid"}
    try:
        parse_record_safely(sample)
    except DataValidationError as err:
        print("Caught Expected Validation Error:", err)
