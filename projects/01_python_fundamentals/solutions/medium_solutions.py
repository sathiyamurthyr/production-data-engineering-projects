"""Solution for Medium Level Exercises."""
from typing import List, Dict, Any

def compute_cumulative_sales(daily_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    running_total = 0.0
    result = []
    for rec in daily_records:
        sales = float(rec.get("sales", 0.0))
        running_total += sales
        result.append({**rec, "cumulative_sales": round(running_total, 2)})
    return result
