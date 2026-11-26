"""
================================================================================
MODULE 04: String Manipulation & Normalization
================================================================================

1. EXPLANATION:
--------------------------------------------------------------------------------
Strings are immutable byte/character sequences. Data pipelines spend significant processing power
cleaning strings: trimming whitespace, lowercasing, converting column names to snake_case,
and masking PII strings.

2. BUSINESS USE CASE:
--------------------------------------------------------------------------------
Normalize raw incoming CSV header names into sanitized SQL column names.

3. PRODUCTION EXAMPLE:
--------------------------------------------------------------------------------
Sanitizes raw string headers into valid database identifier columns.

4. EXPECTED OUTPUT:
--------------------------------------------------------------------------------
[INFO] Original Header: ' Customer First Name ' -> Sanitized: 'customer_first_name'
"""

import re
from typing import List

def to_snake_case(header_name: str) -> str:
    """Convert messy string headers into clean snake_case column names."""
    clean = header_name.strip()
    clean = re.sub(r'[^\w\s]', '', clean)
    clean = re.sub(r'\s+', '_', clean)
    return clean.lower()

def sanitize_headers(raw_headers: List[str]) -> List[str]:
    """Sanitize an entire list of raw column headers."""
    return [to_snake_case(h) for h in raw_headers]

if __name__ == "__main__":
    headers = [" Customer First Name ", "Transaction Amount ($)", "Order Date Time!"]
    sanitized = sanitize_headers(headers)
    print("Sanitized Headers:", sanitized)
