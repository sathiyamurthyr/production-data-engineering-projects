"""Glossary Service - CRUD and search operations for business terms."""

from typing import Any
from uuid import UUID

from pymongo import MongoClient
from pymongo.collection import Collection

from .models import Term, Category


class GlossaryService:
    """Manage business glossary terms and categories."""

    def __init__(self, connection_string: str, database: str = "datafabric") -> None:
        """Initialize service with MongoDB connection."""
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
        self.terms: Collection = self.db.terms
        self.categories: Collection = self.db.categories
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create database indexes."""
        self.terms.create_index("name", unique=True)

    def create_term(self, term: Term) -> Term:
        """Create a new business term."""
        self.terms.insert_one(term.model_dump())
        return term

    def get_term(self, term_id: UUID) -> Term | None:
        """Get term by ID."""
        doc = self.terms.find_one({"id": str(term_id)})
        if doc:
            return Term(**doc)
        return None

    def get_term_by_name(self, name: str) -> Term | None:
        """Get term by name."""
        doc = self.terms.find_one({"name": name})
        if doc:
            return Term(**doc)
        return None

    def update_term(self, term_id: UUID, updates: dict[str, Any]) -> Term | None:
        """Update term properties."""
        result = self.terms.find_one_and_update(
            {"id": str(term_id)},
            {"$set": updates},
            return_document=True,
        )
        if result:
            return Term(**result)
        return None

    def search_terms(self, query: str) -> list[Term]:
        """Search terms by name or definition."""
        cursor = self.terms.find({
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"definition": {"$regex": query, "$options": "i"}},
            ]
        })
        return [Term(**doc) for doc in cursor]

    def auto_discover_terms(self, assets: list[dict[str, Any]]) -> list[Term]:
        """Auto-discover potential business terms from assets."""
        potential_terms = []
        # Logic to suggest terms based on column patterns
        return potential_terms

    def close(self) -> None:
        """Close database connection."""
        self.client.close()