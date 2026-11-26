"""Tests for OntologyRegistry schema inheritance, validation, and compatibility."""

from pathlib import Path
import pytest

from src.schema.ontology_registry import (
    OntologyRegistry,
    OntologyValidationError,
    check_backward_compatibility,
)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "configs" / "ontology_schema.yaml"


def test_ontology_registry_validates_inheritance_and_rejects_abstract_class() -> None:
    registry = OntologyRegistry.from_yaml(SCHEMA_PATH)

    assert registry.is_subclass_of("Customer", "LegalEntity")
    assert registry.is_subclass_of("Merchant", "LegalEntity")
    assert set(registry.get_subclasses("LegalEntity")) == {"LegalEntity", "Customer", "Merchant"}

    # Abstract LegalEntity cannot be instantiated directly
    with pytest.raises(OntologyValidationError, match="abstract"):
        registry.validate_instance("LegalEntity", {"entity_id": "le_1", "display_name": "Test"})

    # Customer inherits country default="IN" and validates tier enum
    normalized = registry.validate_instance(
        "Customer",
        {"entity_id": "c1", "display_name": "Alice", "email": "alice@example.com"},
    )
    assert normalized["country"] == "IN"
    assert normalized["tier"] == "BRONZE"

    # Invalid enum fails closed
    with pytest.raises(OntologyValidationError, match="allowed="):
        registry.validate_instance(
            "Customer",
            {
                "entity_id": "c1",
                "display_name": "Alice",
                "email": "alice@example.com",
                "tier": "DIAMOND",
            },
        )


def test_ontology_relationship_domain_range_polymorphism() -> None:
    registry = OntologyRegistry.from_yaml(SCHEMA_PATH)

    # Merchant is a subclass of LegalEntity, so SUBSIDIARY_OF is valid
    spec = registry.validate_relationship("SUBSIDIARY_OF", "Merchant", "Merchant")
    assert spec.transitive is True

    # Order cannot PLACED_ORDER Customer (inverted domain/range)
    with pytest.raises(OntologyValidationError, match="domain"):
        registry.validate_relationship("PLACED_ORDER", "Order", "Customer")


def test_backward_compatibility_checker_flags_breaking_changes() -> None:
    v1 = OntologyRegistry.from_yaml(SCHEMA_PATH)
    v2 = OntologyRegistry.from_dict(
        {
            "version": "2.0.0",
            "namespace": "urn:de:ontology:",
            "classes": {
                "LegalEntity": {
                    "abstract": True,
                    "primary_key": "entity_id",
                    "properties": {
                        "entity_id": {"type": "string", "required": True},
                        "display_name": {"type": "string", "required": True},
                    },
                },
                "Customer": {
                    "parent": "LegalEntity",
                    "primary_key": "entity_id",
                    "properties": {
                        "entity_id": {"type": "string", "required": True},
                        "display_name": {"type": "string", "required": True},
                        "email": {"type": "string", "required": True},
                        "kyc_id": {"type": "string", "required": True},
                    },
                },
            },
            "relationships": {},
        }
    )

    breaking = check_backward_compatibility(v1, v2)
    assert any("Removed class 'Merchant'" in item for item in breaking)
    assert any("Added required property 'Customer.kyc_id'" in item for item in breaking)
    assert any("Removed relationship 'PLACED_ORDER'" in item for item in breaking)
