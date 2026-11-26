"""Mapping and entity resolution package exports."""

from src.mapping.entity_resolver import (
    CustomerEntityResolver,
    normalize_email,
    normalize_name,
    token_jaccard_similarity,
)

__all__ = [
    "CustomerEntityResolver",
    "normalize_email",
    "normalize_name",
    "token_jaccard_similarity",
]
