"""End-to-end incremental RAG data engineering pipeline orchestrator."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import yaml

from src.chunking.chunker import DocumentChunker
from src.embeddings.embedder import (
    BaseEmbedder,
    DeterministicHashEmbedder,
    OpenAICompatibleEmbedder,
    estimate_embedding_cost_usd,
)
from src.ingestion.document_loader import DocumentLoader
from src.ingestion.incremental_sync import IncrementalSyncTracker
from src.models import PipelineRunReport, SanitizedDocument, SearchResult
from src.quality.content_guardrails import ContentGuardrails
from src.quality.pii_sanitizer import PIISanitizer
from src.vector_store.sqlite_vector_store import SQLiteVectorStore


class RAGIngestionPipeline:
    """Orchestrates incremental document ingestion, sanitization, chunking, embedding, and upsert."""

    def __init__(self, config: Dict[str, Any], base_dir: str | Path = ".") -> None:
        self.base_dir = Path(base_dir)
        self.config = config

        pipe_cfg = config.get("pipeline", {})
        ing_cfg = config.get("ingestion", {})
        qual_cfg = config.get("quality", {})
        chunk_cfg = config.get("chunking", {})
        emb_cfg = config.get("embeddings", {})
        ret_cfg = config.get("retrieval", {})

        self.state_db_path = self._resolve_path(pipe_cfg.get("state_db_path", "output/state.sqlite"))
        self.audit_log_path = self._resolve_path(
            pipe_cfg.get("audit_log_path", "output/pipeline_audit.jsonl")
        )
        self.quarantine_path = self._resolve_path(
            pipe_cfg.get("quarantine_path", "output/quarantined_docs.jsonl")
        )

        self.loader = DocumentLoader(
            default_acl_group=ing_cfg.get("default_acl_group", "engineering")
        )
        self.sync_tracker = IncrementalSyncTracker(self.state_db_path)
        self.sanitizer = PIISanitizer(
            quarantine_on_secret=qual_cfg.get("pii_redaction", {}).get("quarantine_on_secret", True)
        )
        dedup_cfg = qual_cfg.get("deduplication", {})
        self.guardrails = ContentGuardrails(
            min_chars=qual_cfg.get("min_chars", 40),
            max_chars=qual_cfg.get("max_chars", 50_000),
            shingle_size=dedup_cfg.get("shingle_size", 3),
            jaccard_threshold=dedup_cfg.get("jaccard_threshold", 0.85),
        )
        self.dedup_enabled = dedup_cfg.get("enabled", True)
        self.pii_enabled = qual_cfg.get("pii_redaction", {}).get("enabled", True)

        self.chunker = DocumentChunker(
            strategy=chunk_cfg.get("strategy", "markdown_aware"),
            max_tokens=chunk_cfg.get("max_tokens", 180),
            overlap_tokens=chunk_cfg.get("overlap_tokens", 30),
            min_chunk_tokens=chunk_cfg.get("min_chunk_tokens", 15),
        )
        self.embedder: BaseEmbedder = self._build_embedder(emb_cfg)
        self.cost_per_1m = float(emb_cfg.get("cost_per_1m_tokens_usd", 0.02))
        self.vector_store = SQLiteVectorStore(
            self.state_db_path, rrf_k=int(ret_cfg.get("rrf_k", 60))
        )
        self.default_top_k = int(ret_cfg.get("default_top_k", 5))
        self.default_mode = str(ret_cfg.get("mode", "hybrid_rrf"))

    @classmethod
    def from_yaml(cls, config_path: str | Path, base_dir: Optional[str | Path] = None) -> "RAGIngestionPipeline":
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle)
        resolved_base = Path(base_dir) if base_dir is not None else path.parent.parent
        return cls(cfg, base_dir=resolved_base)

    def run(self, source_dir: str | Path) -> PipelineRunReport:
        """Execute one incremental ingestion and indexing run."""
        run_id = uuid.uuid4().hex[:12]
        started_at = datetime.now(timezone.utc).isoformat()

        raw_docs = self.loader.load_directory(self._resolve_path(source_dir))
        plan = self.sync_tracker.compute_sync_plan(raw_docs)
        docs_to_process = plan.new_docs + plan.modified_docs

        chunks_upserted = 0
        chunks_deleted = 0
        tokens_embedded = 0
        docs_quarantined = 0
        docs_deduplicated = 0
        pii_redactions_total = 0

        # Handle deleted documents first
        if plan.deleted_doc_ids:
            chunks_deleted += self.vector_store.delete_by_doc_ids(plan.deleted_doc_ids)
            self.sync_tracker.mark_deleted(plan.deleted_doc_ids)

        for raw_doc in docs_to_process:
            sanitized = (
                self.sanitizer.sanitize_document(raw_doc)
                if self.pii_enabled
                else SanitizedDocument(
                    doc_id=raw_doc.doc_id,
                    source_uri=raw_doc.source_uri,
                    title=raw_doc.title,
                    cleaned_content=raw_doc.content,
                    content_hash=raw_doc.content_hash,
                    acl_group=raw_doc.acl_group,
                    source_type=raw_doc.source_type,
                    metadata=dict(raw_doc.metadata),
                )
            )
            pii_redactions_total += sum(sanitized.pii_redactions.values())
            sanitized = self.guardrails.validate(sanitized)

            if sanitized.quarantined:
                docs_quarantined += 1
                chunks_deleted += self.vector_store.delete_by_doc_ids([raw_doc.doc_id])
                self._append_jsonl(
                    self.quarantine_path,
                    {
                        "run_id": run_id,
                        "doc_id": raw_doc.doc_id,
                        "source_uri": raw_doc.source_uri,
                        "reason": sanitized.quarantine_reason,
                    },
                )
                continue

            if self.dedup_enabled and self.guardrails.is_near_duplicate(sanitized.cleaned_content):
                docs_deduplicated += 1
                continue

            chunks = self.chunker.chunk_document(sanitized)
            embedded_chunks = self.embedder.embed_chunks(chunks)
            tokens_embedded += sum(item.chunk.token_count for item in embedded_chunks)
            chunks_upserted += self.vector_store.replace_document_chunks(
                raw_doc.doc_id, embedded_chunks
            )
            self.sync_tracker.mark_synced(raw_doc, chunk_count=len(embedded_chunks))

        finished_at = datetime.now(timezone.utc).isoformat()
        report = PipelineRunReport(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            docs_scanned=len(raw_docs),
            docs_new=len(plan.new_docs),
            docs_modified=len(plan.modified_docs),
            docs_unchanged=len(plan.unchanged_docs),
            docs_deleted=len(plan.deleted_doc_ids),
            docs_quarantined=docs_quarantined,
            docs_deduplicated=docs_deduplicated,
            chunks_upserted=chunks_upserted,
            chunks_deleted=chunks_deleted,
            tokens_embedded=tokens_embedded,
            estimated_cost_usd=estimate_embedding_cost_usd(tokens_embedded, self.cost_per_1m),
            pii_redactions_total=pii_redactions_total,
            status="SUCCESS",
        )
        self._append_jsonl(self.audit_log_path, asdict(report))
        return report

    def query(
        self,
        query_text: str,
        top_k: Optional[int] = None,
        acl_groups: Optional[List[str]] = None,
        mode: Optional[str] = None,
    ) -> List[SearchResult]:
        """Run ACL-scoped hybrid or vector search against the indexed chunks."""
        vec = self.embedder.embed_query(query_text)
        return self.vector_store.search(
            query_text=query_text,
            query_vector=vec,
            top_k=top_k or self.default_top_k,
            acl_groups=acl_groups,
            mode=mode or self.default_mode,
        )

    def _build_embedder(self, emb_cfg: Dict[str, Any]) -> BaseEmbedder:
        provider = emb_cfg.get("provider", "local_deterministic")
        dims = int(emb_cfg.get("dimensions", 128))
        batch_size = int(emb_cfg.get("batch_size", 16))
        model_name = str(emb_cfg.get("model_name", "local-hash-v1"))
        if provider == "local_deterministic":
            return DeterministicHashEmbedder(
                model_name=model_name, dimensions=dims, batch_size=batch_size
            )
        if provider == "openai_compatible":
            return OpenAICompatibleEmbedder(
                model_name=model_name,
                dimensions=dims,
                batch_size=batch_size,
                max_retries=int(emb_cfg.get("max_retries", 3)),
            )
        raise ValueError(f"Unsupported embedding provider: {provider}")

    def _resolve_path(self, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        return path if path.is_absolute() else self.base_dir / path

    @staticmethod
    def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
