"""Cross-source entity resolution and canonical URI mapping."""

import hashlib
import re
from typing import Any, Dict, List, Sequence

from src.models import ResolvedEntity


TIER_PRIORITY = {"PLATINUM": 4, "GOLD": 3, "SILVER": 2, "BRONZE": 1}


def normalize_email(email: str) -> str:
    """Lowercase and trim email addresses for deterministic blocking."""
    return email.strip().lower()


def normalize_name(name: str) -> str:
    """Collapse whitespace and punctuation for fuzzy name comparison."""
    cleaned = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    return " ".join(cleaned.split())


def token_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Compute token-level Jaccard similarity between two normalized strings."""
    tokens_a = set(normalize_name(text_a).split())
    tokens_b = set(normalize_name(text_b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


class CustomerEntityResolver:
    """
    Resolves duplicate CRM/source customer records into canonical Ontology entities
    using email blocking keys and token similarity survivorship rules.
    """

    def __init__(self, namespace: str = "urn:de:ontology:") -> None:
        self.namespace = namespace

    def canonical_id_for_email(self, email: str) -> str:
        norm_email = normalize_email(email)
        digest = hashlib.sha256(norm_email.encode("utf-8")).hexdigest()[:12]
        return f"cust_{digest}"

    def resolve_customers(self, raw_rows: Sequence[Dict[str, Any]]) -> List[ResolvedEntity]:
        """Group raw customer rows by normalized email and apply survivorship rules."""
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for row in raw_rows:
            email = normalize_email(str(row.get("email", "")))
            if not email:
                continue
            buckets.setdefault(email, []).append(row)

        resolved: List[ResolvedEntity] = []
        for email in sorted(buckets):
            group = buckets[email]
            canonical_id = self.canonical_id_for_email(email)
            canonical_uri = f"{self.namespace}customer:{canonical_id}"

            # Survivorship: prefer longest display_name, highest loyalty tier
            names = [str(r.get("full_name") or r.get("display_name") or "").strip() for r in group]
            best_name = max(names, key=lambda n: len(n))
            tiers = [str(r.get("tier") or "BRONZE").upper() for r in group]
            best_tier = max(tiers, key=lambda t: TIER_PRIORITY.get(t, 0))
            countries = [str(r.get("country") or "IN").upper() for r in group if r.get("country")]
            best_country = countries[0] if countries else "IN"

            source_ids = [str(r.get("source_id") or r.get("id")) for r in group]
            confidence = 1.0
            if len(group) > 1:
                sims = [token_jaccard_similarity(names[0], other) for other in names[1:]]
                avg_sim = sum(sims) / len(sims)
                confidence = round(0.8 + (0.2 * avg_sim), 4)

            resolved.append(
                ResolvedEntity(
                    canonical_uri=canonical_uri,
                    canonical_id=canonical_id,
                    class_name="Customer",
                    properties={
                        "entity_id": canonical_id,
                        "display_name": best_name,
                        "email": email,
                        "tier": best_tier,
                        "country": best_country,
                    },
                    source_ids=source_ids,
                    merge_confidence=confidence,
                )
            )
        return resolved
