"""
================================================================================
MODULE 11: Lambda & Anonymous Functions
================================================================================
1. EXPLANATION:
Lambda expressions define inline single-expression functions, commonly passed to `map()`, `filter()`,
or sorting functions (`sorted(data, key=lambda x: x['amount'])`).

2. BUSINESS USE CASE:
Sort pipeline transaction records by timestamp or amount on the fly.
"""
from typing import List, Dict, Any

def sort_transactions_by_amount(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort transaction records descending by amount using lambda key."""
    return sorted(records, key=lambda r: r.get("amount", 0.0), reverse=True)

if __name__ == "__main__":
    txns = [{"id": 1, "amount": 50}, {"id": 2, "amount": 500}, {"id": 3, "amount": 150}]
    sorted_txns = sort_transactions_by_amount(txns)
    print("Sorted Transactions:", sorted_txns)
