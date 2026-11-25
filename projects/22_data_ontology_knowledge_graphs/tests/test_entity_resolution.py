"""Tests for cross-source customer entity resolution and merge survivorship."""

from src.mapping.entity_resolver import CustomerEntityResolver, token_jaccard_similarity


def test_customer_entity_resolver_merges_email_duplicates_with_lineage() -> None:
    resolver = CustomerEntityResolver()
    raw_rows = [
        {
            "source_id": "crm_101",
            "full_name": "Aarav Sharma",
            "email": "aarav.sharma@example.com",
            "tier": "SILVER",
            "country": "IN",
        },
        {
            "source_id": "crm_103",
            "full_name": "Aarav K. Sharma",
            "email": "AARAV.SHARMA@example.com",
            "tier": "GOLD",
            "country": "IN",
        },
        {
            "source_id": "crm_102",
            "full_name": "Priya Nair",
            "email": "priya.nair@example.com",
            "tier": "PLATINUM",
            "country": "IN",
        },
    ]

    resolved = resolver.resolve_customers(raw_rows)
    assert len(resolved) == 2

    aarav = next(e for e in resolved if e.properties["email"] == "aarav.sharma@example.com")
    assert aarav.source_ids == ["crm_101", "crm_103"]
    assert aarav.properties["display_name"] == "Aarav K. Sharma"
    assert aarav.properties["tier"] == "GOLD"
    assert 0.8 < aarav.merge_confidence <= 1.0
    assert token_jaccard_similarity("Aarav Sharma", "Aarav K. Sharma") > 0.5
