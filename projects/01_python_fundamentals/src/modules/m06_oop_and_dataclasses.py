"""
Module 21-25: Virtual Environments, Modules, Packages, OOP, and Dataclasses.

Explanation:
Object-Oriented Programming (OOP) and Dataclasses structure pipeline state, data contracts, and connectors.
- Dataclasses: Strongly-typed data containers replacing raw untyped dicts.
- OOP: Base classes for Extractors, Transformers, Loaders.

Business Use Case:
Define an enterprise transaction contract using Dataclasses and an abstract Extractor class.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class TransactionEvent:
    """Enterprise Data Contract for Transaction Events."""
    transaction_id: str
    customer_id: str
    amount: float
    status: str
    timestamp: str
    ingested_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def is_valid(self) -> bool:
        return self.amount >= 0.0 and len(self.transaction_id) > 0

class BaseExtractor:
    """Abstract Base Class for Data Pipeline Extractors."""
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    def extract(self) -> list:
        raise NotImplementedError("Subclasses must implement extract()")
