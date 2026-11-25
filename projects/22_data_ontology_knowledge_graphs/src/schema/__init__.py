"""Schema package exports."""

from src.schema.ontology_registry import (
    OntologyRegistry,
    OntologyValidationError,
    check_backward_compatibility,
)

__all__ = [
    "OntologyRegistry",
    "OntologyValidationError",
    "check_backward_compatibility",
]
