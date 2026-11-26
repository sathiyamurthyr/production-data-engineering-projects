"""Data contracts for AI / LLM Data Engineering Pipelines."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RawDocument:
    """Immutable representation of an ingested unstructured/semi-structured document."""

    doc_id: str
    source_uri: str
    title: str
    content: str
    content_hash: str
    acl_group: str = "engineering"
    source_type: str = "markdown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SanitizedDocument:
    """Document after PII redaction and content quality validation."""

    doc_id: str
    source_uri: str
    title: str
    cleaned_content: str
    content_hash: str
    acl_group: str
    source_type: str
    pii_redactions: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    quarantined: bool = False
    quarantine_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TextChunk:
    """Token-bounded text chunk with deterministic ID and lineage metadata."""

    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    token_count: int
    heading_path: str
    acl_group: str
    source_uri: str
    content_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddedChunk:
    """Vector-encoded chunk ready for atomic upsert into a vector store."""

    chunk: TextChunk
    embedding: List[float]
    model_name: str


@dataclass(frozen=True)
class SearchResult:
    """Ranked retrieval result with score breakdown and provenance."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    heading_path: str
    source_uri: str
    acl_group: str
    vector_score: float = 0.0
    lexical_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineRunReport:
    """Operational telemetry and cost accounting for a pipeline run."""

    run_id: str
    started_at: str
    finished_at: str
    docs_scanned: int
    docs_new: int
    docs_modified: int
    docs_unchanged: int
    docs_deleted: int
    docs_quarantined: int
    docs_deduplicated: int
    chunks_upserted: int
    chunks_deleted: int
    tokens_embedded: int
    estimated_cost_usd: float
    pii_redactions_total: int
    status: str = "SUCCESS"
