"""
================================================================================
MODULE 06: Tuples & Immutable Records
================================================================================
1. EXPLANATION:
Tuples are ordered immutable sequences. In DE, tuples represent database rows (e.g. cursor.fetchall())
where values must not be modified accidentally during transformation steps.

2. BUSINESS USE CASE:
Store immutable database row records and return multiple metrics from pipeline functions safely.

3. PRODUCTION EXAMPLE:
Returns immutable pipeline metrics (records_processed, total_revenue, error_count).
"""
from typing import Tuple

def process_batch(records: list) -> Tuple[int, float, int]:
    """Process a batch and return immutable metric tuple: (count, revenue, errors)."""
    count = len(records)
    revenue = sum(r.get("amount", 0.0) for r in records if r.get("status") == "COMPLETED")
    errors = sum(1 for r in records if r.get("status") == "FAILED")
    return (count, revenue, errors)

if __name__ == "__main__":
    batch = [{"amount": 100, "status": "COMPLETED"}, {"amount": 50, "status": "FAILED"}]
    metrics = process_batch(batch)
    print(f"Metrics (Processed, Revenue, Errors): {metrics}")
