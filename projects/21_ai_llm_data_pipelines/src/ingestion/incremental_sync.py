"""Incremental CDC state tracker for LLM document ingestion."""

from contextlib import contextmanager
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Sequence

from src.models import RawDocument


@dataclass(frozen=True)
class SyncPlan:
    """Delta classification of source documents relative to persisted state."""

    new_docs: List[RawDocument]
    modified_docs: List[RawDocument]
    unchanged_docs: List[RawDocument]
    deleted_doc_ids: List[str]


class IncrementalSyncTracker:
    """Tracks document SHA-256 hashes in SQLite to avoid redundant re-embedding."""

    def __init__(self, state_db_path: str | Path) -> None:
        self.db_path = Path(state_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS doc_sync_state (
                    doc_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    acl_group TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def compute_sync_plan(self, incoming_docs: Sequence[RawDocument]) -> SyncPlan:
        """Compare incoming documents against active tracked hashes."""
        existing = self.get_active_hashes()
        incoming_ids = set()
        new_docs: List[RawDocument] = []
        modified_docs: List[RawDocument] = []
        unchanged_docs: List[RawDocument] = []

        for doc in incoming_docs:
            incoming_ids.add(doc.doc_id)
            prev_hash = existing.get(doc.doc_id)
            if prev_hash is None:
                new_docs.append(doc)
            elif prev_hash != doc.content_hash:
                modified_docs.append(doc)
            else:
                unchanged_docs.append(doc)

        deleted_doc_ids = sorted(doc_id for doc_id in existing if doc_id not in incoming_ids)
        return SyncPlan(
            new_docs=new_docs,
            modified_docs=modified_docs,
            unchanged_docs=unchanged_docs,
            deleted_doc_ids=deleted_doc_ids,
        )

    def get_active_hashes(self) -> Dict[str, str]:
        """Return mapping of active doc_id -> content_hash."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT doc_id, content_hash FROM doc_sync_state WHERE status = 'ACTIVE'"
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def mark_synced(self, doc: RawDocument, chunk_count: int) -> None:
        """Persist or update document state after successful embedding & upsert."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO doc_sync_state
                    (doc_id, content_hash, source_uri, acl_group, chunk_count, status, updated_at)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    source_uri = excluded.source_uri,
                    acl_group = excluded.acl_group,
                    chunk_count = excluded.chunk_count,
                    status = 'ACTIVE',
                    updated_at = excluded.updated_at
                """,
                (doc.doc_id, doc.content_hash, doc.source_uri, doc.acl_group, chunk_count, now),
            )
            conn.commit()

    def mark_deleted(self, doc_ids: Sequence[str]) -> None:
        """Tombstone deleted documents in state store."""
        if not doc_ids:
            return
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.executemany(
                "UPDATE doc_sync_state SET status = 'DELETED', updated_at = ? WHERE doc_id = ?",
                [(now, doc_id) for doc_id in doc_ids],
            )
            conn.commit()
