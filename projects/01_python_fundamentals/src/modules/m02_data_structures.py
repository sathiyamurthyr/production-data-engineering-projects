"""
Module 05-08: Lists, Tuples, Sets, and Dictionaries in High-Performance Pipelines.

Explanation:
- Lists: Ordered mutable sequences (in-memory batch buffering).
- Tuples: Immutable tuples used for fixed database record structures (id, timestamp, val).
- Sets: Hash-based unique sets for O(1) deduplication and set difference comparisons.
- Dictionaries: Key-value lookup tables for hash joins, column mapping, and state management.

Business Use Case:
Deduplicate incoming event streams using Sets, group transactions by customer using Dictionaries,
and maintain immutable audit tuples for CDC logs.
"""

from typing import Dict, List, Set, Tuple, Any

def deduplicate_and_aggregate_sales(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Module 05-08 Production Example: Deduplicate by transaction_id and aggregate spend per customer.
    """
    seen_ids: Set[str] = set()
    unique_records: List[Dict[str, Any]] = []
    customer_total_spend: Dict[str, float] = {}

    for record in records:
        txn_id = record["transaction_id"]
        if txn_id in seen_ids:
            continue  # Fast O(1) set lookup
        seen_ids.add(txn_id)
        unique_records.append(record)

        cust_id = record["customer_id"]
        amount = float(record.get("amount", 0.0))
        customer_total_spend[cust_id] = customer_total_spend.get(cust_id, 0.0) + amount

    return unique_records, customer_total_spend

if __name__ == "__main__":
    raw_data = [
        {"transaction_id": "T1", "customer_id": "C1", "amount": 100.0},
        {"transaction_id": "T1", "customer_id": "C1", "amount": 100.0},  # Duplicate
        {"transaction_id": "T2", "customer_id": "C2", "amount": 250.0},
        {"transaction_id": "T3", "customer_id": "C1", "amount": 50.0},
    ]
    deduped, spend = deduplicate_and_aggregate_sales(raw_data)
    print("Deduplicated count:", len(deduped))
    print("Customer Spend Map:", spend)
