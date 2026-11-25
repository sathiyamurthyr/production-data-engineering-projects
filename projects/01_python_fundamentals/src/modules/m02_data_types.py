"""
================================================================================
MODULE 02: Data Types in Data Engineering
================================================================================

1. EXPLANATION:
--------------------------------------------------------------------------------
Data types dictate how numbers, strings, booleans, and nulls are represented in memory.
In data engineering, explicit type casting (str -> float, str -> int) is mandatory when parsing
untyped CSV or JSON strings before pushing to typed SQL or Lakehouse tables.

2. BUSINESS USE CASE:
--------------------------------------------------------------------------------
API and CSV data streams return strings like "1299.99" or "None". We must safely cast amounts to float,
quantities to int, and handle missing (NULL) values without throwing unhandled exceptions.

3. PRODUCTION EXAMPLE:
--------------------------------------------------------------------------------
Parses raw string dictionaries into strictly typed data records with robust type safety.

4. EXPECTED OUTPUT:
--------------------------------------------------------------------------------
[INFO] Parsed record TXN101: Amount=1299.99 (float), Qty=5 (int), Active=True (bool)

5. BEST PRACTICES:
--------------------------------------------------------------------------------
- Always handle None or "NULL" strings before type casting.
- Use Decimal for exact financial calculations to prevent floating point inaccuracy.

6. COMMON MISTAKES:
--------------------------------------------------------------------------------
- Calling float("NULL") directly causing ValueError pipeline crashes.
- Assuming API booleans are always Python booleans (e.g. string "false" is truthy in Python).

7. PERFORMANCE NOTES:
--------------------------------------------------------------------------------
Primitive types (int, float, bool) are immutable in Python.

8. INTERVIEW QUESTIONS & ANSWERS:
--------------------------------------------------------------------------------
Q: Why is float dangerous for financial transaction amounts in data engineering?
A: Binary floating-point representation (IEEE 754) causes precision errors (e.g., 0.1 + 0.2 != 0.3).
   Use the `decimal.Decimal` module for currency calculations.
"""

from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("m02_data_types")

def parse_typed_transaction(raw_data: Dict[str, str]) -> Dict[str, Any]:
    """Parse raw string values into strict Python data types."""
    txn_id: str = str(raw_data.get("txn_id", "")).strip()
    
    # Safe float/decimal conversion
    amount_str = raw_data.get("amount", "0.0")
    try:
        amount: Decimal = Decimal(str(amount_str))
    except (InvalidOperation, ValueError):
        logger.warning(f"Invalid amount '{amount_str}' for TXN {txn_id}. Defaulting to 0.00")
        amount = Decimal("0.00")

    # Safe int conversion
    qty_str = raw_data.get("quantity", "0")
    qty: int = int(qty_str) if str(qty_str).isdigit() else 0

    # Safe boolean conversion
    is_active: bool = str(raw_data.get("is_active", "")).lower() in ("true", "1", "yes")

    return {
        "txn_id": txn_id,
        "amount": amount,
        "quantity": qty,
        "is_active": is_active
    }

if __name__ == "__main__":
    raw = {"txn_id": "TXN101", "amount": "1299.99", "quantity": "5", "is_active": "true"}
    typed = parse_typed_transaction(raw)
    print(f"Parsed Record: {typed}")
