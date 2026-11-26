"""Pre-embedding PII and secret sanitization for LLM/RAG pipelines."""

import re
from typing import Dict, Pattern, Tuple

from src.models import RawDocument, SanitizedDocument


class PIISanitizer:
    """Redacts PII and sensitive credentials before text enters vector embeddings."""

    DEFAULT_PATTERNS: Dict[str, Tuple[Pattern[str], str]] = {
        "API_KEY": (
            re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,})\b"),
            "[REDACTED_SECRET]",
        ),
        "SSN": (
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "[REDACTED_SSN]",
        ),
        "CREDIT_CARD": (
            re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
            "[REDACTED_CARD]",
        ),
        "EMAIL": (
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "[REDACTED_EMAIL]",
        ),
        "PHONE": (
            re.compile(r"(?<!\w)(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
            "[REDACTED_PHONE]",
        ),
    }

    def __init__(self, quarantine_on_secret: bool = True) -> None:
        self.quarantine_on_secret = quarantine_on_secret

    def sanitize_document(self, doc: RawDocument) -> SanitizedDocument:
        """Apply regex redactions and flag documents containing raw secrets."""
        cleaned = doc.content
        redactions: Dict[str, int] = {}

        for label, (pattern, replacement) in self.DEFAULT_PATTERNS.items():
            cleaned, count = pattern.subn(replacement, cleaned)
            if count > 0:
                redactions[label] = count

        quarantined = False
        quarantine_reason = None
        if self.quarantine_on_secret and redactions.get("API_KEY", 0) > 0:
            quarantined = True
            quarantine_reason = "Raw API credential detected in source document"

        return SanitizedDocument(
            doc_id=doc.doc_id,
            source_uri=doc.source_uri,
            title=doc.title,
            cleaned_content=cleaned,
            content_hash=doc.content_hash,
            acl_group=doc.acl_group,
            source_type=doc.source_type,
            pii_redactions=redactions,
            quarantined=quarantined,
            quarantine_reason=quarantine_reason,
            metadata=dict(doc.metadata),
        )
