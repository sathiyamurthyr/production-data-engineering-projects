"""
================================================================================
MODULE 25: Dataclasses for Strongly Typed Data Contracts
================================================================================
1. EXPLANATION:
`@dataclass` generates boilerplate methods (`__init__`, `__repr__`, `__eq__`) for clean data structures.

2. BUSINESS USE CASE:
Define an immutable sales transaction data contract.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class SalesRecord:
    """Immutable Data Contract for Sales Record."""
    transaction_id: str
    amount: float
    category: str

    def is_valid(self) -> bool:
        return self.amount >= 0.0 and len(self.transaction_id) > 0

if __name__ == "__main__":
    rec = SalesRecord("TXN900", 299.99, "Electronics")
    print(f"Record: {rec}, Valid: {rec.is_valid()}")
