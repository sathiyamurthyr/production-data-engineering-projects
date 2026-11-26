"""
================================================================================
MODULE 08: Dictionaries & Key-Value Lookup Tables
================================================================================
1. EXPLANATION:
Dictionaries implement hash maps for O(1) key-value lookup. In DE, dictionaries represent JSON rows,
column maps, aggregate accumulators, and lookup join tables.

2. BUSINESS USE CASE:
Perform efficient broadcast joins in memory using dictionary lookup tables.
"""
from typing import List, Dict, Any

def enrich_sales_with_customer(
    sales: List[Dict[str, Any]], customer_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Enrich sales records with customer names using O(1) dictionary lookup."""
    enriched = []
    for s in sales:
        c_id = s.get("customer_id", "")
        c_name = customer_map.get(c_id, "Unknown Customer")
        enriched.append({**s, "customer_name": c_name})
    return enriched

if __name__ == "__main__":
    sales_data = [{"txn": "T1", "customer_id": "C1", "amount": 100}]
    cust_lookup = {"C1": "Acme Corp", "C2": "Globex Inc"}
    res = enrich_sales_with_customer(sales_data, cust_lookup)
    print("Enriched Record:", res)
