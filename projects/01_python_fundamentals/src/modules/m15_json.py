"""
================================================================================
MODULE 15: JSON Serialization & Parsing
================================================================================
1. EXPLANATION:
JSON is the standard format for REST APIs and semi-structured data logs. In DE, `json.loads()`/`json.dumps()`
and `json.load()`/`json.dump()` parse payloads and write metadata metrics.

2. BUSINESS USE CASE:
Parse nested JSON API responses and flatten attributes into tabular analytical rows.
"""
import json
from typing import Dict, Any, List

def flatten_user_json(json_str: str) -> List[Dict[str, Any]]:
    """Parse JSON payload and flatten nested user address data."""
    users = json.loads(json_str)
    flattened = []
    for u in users:
        flattened.append({
            "user_id": u["id"],
            "name": u["name"],
            "city": u.get("address", {}).get("city", "N/A"),
            "zipcode": u.get("address", {}).get("zipcode", "N/A")
        })
    return flattened

if __name__ == "__main__":
    raw_json = '''[
        {"id": "U1", "name": "Alice", "address": {"city": "New York", "zipcode": "10001"}},
        {"id": "U2", "name": "Bob", "address": {"city": "London", "zipcode": "EC1A"}}
    ]'''
    flat = flatten_user_json(raw_json)
    print("Flattened JSON Data:", flat)
