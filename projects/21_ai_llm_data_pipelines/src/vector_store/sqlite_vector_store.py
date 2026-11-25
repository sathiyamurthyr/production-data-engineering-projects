"""SQLite-backed Vector & Hybrid Search Store with ACL metadata filtering."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from src.models import EmbeddedChunk, SearchResult


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute cosine similarity between two equal-length float vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class BaseVectorStore(ABC):
    """Abstract contract for vector store implementations (SQLite, pgvector, Qdrant)."""

    @abstractmethod
    def replace_document_chunks(self, doc_id: str, chunks: Sequence[EmbeddedChunk]) -> int:
        """Atomically replace all chunks belonging to doc_id."""

    @abstractmethod
    def delete_by_doc_ids(self, doc_ids: Sequence[str]) -> int:
        """Delete all chunks for the specified document IDs."""

    @abstractmethod
    def search(
        self,
        query_text: str,
        query_vector: Sequence[float],
        top_k: int = 5,
        acl_groups: Optional[Sequence[str]] = None,
        mode: str = "hybrid_rrf",
    ) -> List[SearchResult]:
        """Retrieve top-K ranked chunks with optional ACL pre-filtering."""

    @abstractmethod
    def count_chunks(self) -> int:
        """Return total stored chunk count."""


class SQLiteVectorStore(BaseVectorStore):
    """Persistent SQLite vector store supporting cosine, lexical BM25-like, and hybrid RRF."""

    WORD_RE = re.compile(r"[a-z0-9_]+")

    def __init__(self, db_path: str | Path, rrf_k: int = 60) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.rrf_k = rrf_k
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    heading_path TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    acl_group TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vector_chunks_doc_id ON vector_chunks(doc_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vector_chunks_acl ON vector_chunks(acl_group)"
            )
            conn.commit()

    def replace_document_chunks(self, doc_id: str, chunks: Sequence[EmbeddedChunk]) -> int:
        """Atomically delete stale chunks for doc_id and insert current chunks."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM vector_chunks WHERE doc_id = ?", (doc_id,))
            conn.executemany(
                """
                INSERT INTO vector_chunks (
                    chunk_id, doc_id, chunk_index, text, embedding_json, model_name,
                    heading_path, source_uri, acl_group, content_hash, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.chunk.chunk_id,
                        item.chunk.doc_id,
                        item.chunk.chunk_index,
                        item.chunk.text,
                        json.dumps(item.embedding),
                        item.model_name,
                        item.chunk.heading_path,
                        item.chunk.source_uri,
                        item.chunk.acl_group,
                        item.chunk.content_hash,
                        json.dumps(item.chunk.metadata),
                        now,
                    )
                    for item in chunks
                ],
            )
            conn.commit()
        return len(chunks)

    def delete_by_doc_ids(self, doc_ids: Sequence[str]) -> int:
        """Remove all chunks belonging to deleted or quarantined source documents."""
        if not doc_ids:
            return 0
        placeholders = ",".join("?" for _ in doc_ids)
        with self._connect() as conn:
            cur = conn.execute(
                f"DELETE FROM vector_chunks WHERE doc_id IN ({placeholders})",
                tuple(doc_ids),
            )
            conn.commit()
            return cur.rowcount

    def count_chunks(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM vector_chunks").fetchone()
        return int(row[0]) if row else 0

    def search(
        self,
        query_text: str,
        query_vector: Sequence[float],
        top_k: int = 5,
        acl_groups: Optional[Sequence[str]] = None,
        mode: str = "hybrid_rrf",
    ) -> List[SearchResult]:
        if mode not in {"vector", "lexical", "hybrid_rrf"}:
            raise ValueError(f"Unsupported retrieval mode: {mode}")

        rows = self._fetch_candidate_rows(acl_groups)
        if not rows:
            return []

        query_terms = self.WORD_RE.findall(query_text.lower())
        scored_rows: List[Tuple[dict, float, float]] = []
        for row in rows:
            vec_score = cosine_similarity(query_vector, row["embedding"])
            lex_score = self._lexical_overlap_score(query_terms, row["text"])
            scored_rows.append((row, vec_score, lex_score))

        if mode == "vector":
            ranked = sorted(scored_rows, key=lambda item: item[1], reverse=True)
            return [self._to_result(r, vs, vs, ls) for r, vs, ls in ranked[:top_k]]

        if mode == "lexical":
            ranked = sorted(scored_rows, key=lambda item: item[2], reverse=True)
            return [self._to_result(r, ls, vs, ls) for r, vs, ls in ranked[:top_k]]

        # Hybrid Reciprocal Rank Fusion (RRF)
        vec_order = sorted(range(len(scored_rows)), key=lambda i: scored_rows[i][1], reverse=True)
        lex_order = sorted(range(len(scored_rows)), key=lambda i: scored_rows[i][2], reverse=True)

        vec_ranks = {idx: rank for rank, idx in enumerate(vec_order, start=1)}
        lex_ranks = {idx: rank for rank, idx in enumerate(lex_order, start=1)}

        fused: List[Tuple[dict, float, float, float]] = []
        for idx, (row, vs, ls) in enumerate(scored_rows):
            rrf_score = (1.0 / (self.rrf_k + vec_ranks[idx])) + (
                1.0 / (self.rrf_k + lex_ranks[idx])
            )
            fused.append((row, rrf_score, vs, ls))

        fused.sort(key=lambda item: item[1], reverse=True)
        return [self._to_result(r, score, vs, ls) for r, score, vs, ls in fused[:top_k]]

    def _fetch_candidate_rows(self, acl_groups: Optional[Sequence[str]]) -> List[Dict]:
        query = (
            "SELECT chunk_id, doc_id, text, embedding_json, heading_path, "
            "source_uri, acl_group, metadata_json FROM vector_chunks"
        )
        params: Tuple[str, ...] = ()
        if acl_groups is not None:
            if not acl_groups:
                return []
            placeholders = ",".join("?" for _ in acl_groups)
            query += f" WHERE acl_group IN ({placeholders})"
            params = tuple(acl_groups)

        with self._connect() as conn:
            raw_rows = conn.execute(query, params).fetchall()

        return [
            {
                "chunk_id": row[0],
                "doc_id": row[1],
                "text": row[2],
                "embedding": json.loads(row[3]),
                "heading_path": row[4],
                "source_uri": row[5],
                "acl_group": row[6],
                "metadata": json.loads(row[7]),
            }
            for row in raw_rows
        ]

    def _lexical_overlap_score(self, query_terms: Sequence[str], doc_text: str) -> float:
        if not query_terms:
            return 0.0
        doc_tokens = self.WORD_RE.findall(doc_text.lower())
        if not doc_tokens:
            return 0.0
        doc_vocab = set(doc_tokens)
        unique_query = set(query_terms)
        matches = sum(1 for term in unique_query if term in doc_vocab)
        tf_bonus = sum(min(doc_tokens.count(term), 3) for term in unique_query) / (
            3.0 * len(unique_query)
        )
        return round((0.7 * (matches / len(unique_query))) + (0.3 * tf_bonus), 6)

    @staticmethod
    def _to_result(row: Dict, score: float, vec_score: float, lex_score: float) -> SearchResult:
        return SearchResult(
            chunk_id=row["chunk_id"],
            doc_id=row["doc_id"],
            text=row["text"],
            score=round(score, 6),
            heading_path=row["heading_path"],
            source_uri=row["source_uri"],
            acl_group=row["acl_group"],
            vector_score=round(vec_score, 6),
            lexical_score=round(lex_score, 6),
            metadata=row["metadata"],
        )
