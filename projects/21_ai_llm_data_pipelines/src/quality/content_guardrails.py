"""Content quality, near-duplicate detection, and prompt-injection guardrails."""

import re
from typing import List, Set

from src.models import SanitizedDocument


class ContentGuardrails:
    """Validates document length, detects prompt injections, and removes near-duplicates."""

    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"reveal\s+(?:your\s+)?system\s+prompt", re.IGNORECASE),
        re.compile(r"<\s*system\s*>.*<\s*/\s*system\s*>", re.IGNORECASE | re.DOTALL),
    ]

    def __init__(
        self,
        min_chars: int = 40,
        max_chars: int = 50_000,
        shingle_size: int = 3,
        jaccard_threshold: float = 0.85,
    ) -> None:
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.shingle_size = shingle_size
        self.jaccard_threshold = jaccard_threshold
        self._seen_shingles: List[Set[str]] = []

    def validate(self, doc: SanitizedDocument) -> SanitizedDocument:
        """Check length bounds, prompt injection patterns, and near-duplication."""
        if doc.quarantined:
            return doc

        text = doc.cleaned_content.strip()
        if len(text) < self.min_chars:
            doc.quarantined = True
            doc.quarantine_reason = f"Content shorter than minimum ({len(text)} < {self.min_chars})"
            return doc

        if len(text) > self.max_chars:
            doc.warnings.append(f"Content truncated from {len(text)} to {self.max_chars} chars")
            doc.cleaned_content = text[: self.max_chars]

        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(doc.cleaned_content):
                doc.quarantined = True
                doc.quarantine_reason = "Potential prompt-injection payload detected"
                return doc

        return doc

    def is_near_duplicate(self, text: str) -> bool:
        """Return True if text Jaccard shingle similarity meets/exceeds threshold."""
        shingles = self._build_shingles(text)
        if not shingles:
            return False

        for existing in self._seen_shingles:
            union_size = len(shingles | existing)
            if union_size == 0:
                continue
            similarity = len(shingles & existing) / union_size
            if similarity >= self.jaccard_threshold:
                return True

        self._seen_shingles.append(shingles)
        return False

    def _build_shingles(self, text: str) -> Set[str]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if len(tokens) < self.shingle_size:
            return {" ".join(tokens)} if tokens else set()
        return {
            " ".join(tokens[i : i + self.shingle_size])
            for i in range(len(tokens) - self.shingle_size + 1)
        }
