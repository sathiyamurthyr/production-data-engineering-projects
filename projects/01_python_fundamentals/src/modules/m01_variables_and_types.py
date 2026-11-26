"""
Module 01-04: Variables, Data Types, Operators, and Strings for Data Engineering.

Explanation:
Data engineering pipelines process heterogenous data streams requiring strict dynamic typing,
type casting (e.g., string to float timestamp/amount), string normalization, and operator safety.

Business Use Case:
In ingestion pipelines, raw API payloads or CSV columns deliver string values ("1299.99", "2026-07-20").
We must safely convert types, format column headers, and compute transactional summaries.
"""

from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_transaction_record(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module 01-04 Production Example: Clean and cast a raw transaction record.

    Best Practices:
    - Always validate None / NULL values before casting.
    - Standardize string keys (snake_case, stripped whitespace).
    """
    transaction_id: str = str(raw_record.get("transaction_id", "")).strip().upper()
    amount_raw: Optional[Any] = raw_record.get("amount")

    # Safe float conversion (Operator & Type casting protection)
    amount: float = 0.0
    if amount_raw is not None and str(amount_raw).replace(".", "", 1).isdigit():
        amount = float(amount_raw)
    else:
        logger.warning(f"Invalid amount '{amount_raw}' for TXN {transaction_id}. Defaulting to 0.0.")

    category: str = str(raw_record.get("product_category", "UNKNOWN")).strip().lower().replace(" ", "_")

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "category": category,
        "is_high_value": amount > 500.0  # Comparison operator
    }

if __name__ == "__main__":
    sample = {"transaction_id": " txn1001 ", "amount": "1299.99", "product_category": " Consumer Electronics "}
    cleaned = process_transaction_record(sample)
    logger.info(f"Cleaned Record: {cleaned}")
