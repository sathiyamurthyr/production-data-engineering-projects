"""
Module 09-12: Loops, Functions, Lambda, and List Comprehension.

Explanation:
Loops iterate over micro-batches; list comprehensions offer high-performance C-optimized transformations;
lambdas pass inline transformations to mapping functions; custom functions encapsulate business logic.

Business Use Case:
Filter and transform raw records into bronze tier lakehouse structures using vectorized list comprehensions.
"""

from typing import List, Dict, Any, Callable

def apply_transformations(
    records: List[Dict[str, Any]],
    filter_fn: Callable[[Dict[str, Any]], bool],
    transform_fn: Callable[[Dict[str, Any]], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Module 09-12 Production Example: Functional ETL filter and map pattern.
    """
    # Vectorized list comprehension with inline filtering
    return [transform_fn(r) for r in records if filter_fn(r)]

if __name__ == "__main__":
    data = [
        {"id": 1, "status": "COMPLETED", "amount": 500},
        {"id": 2, "status": "FAILED", "amount": 0},
        {"id": 3, "status": "COMPLETED", "amount": 1200},
    ]
    # Filter completed, apply 10% tax lambda
    transformed = apply_transformations(
        data,
        filter_fn=lambda r: r["status"] == "COMPLETED",
        transform_fn=lambda r: {**r, "total_with_tax": r["amount"] * 1.10}
    )
    print("Transformed:", transformed)
