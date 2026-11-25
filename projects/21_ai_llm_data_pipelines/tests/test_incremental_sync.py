"""Tests for incremental CDC hash tracking (new, modified, unchanged, deleted)."""

from pathlib import Path

from src.ingestion.document_loader import compute_sha256
from src.ingestion.incremental_sync import IncrementalSyncTracker
from src.models import RawDocument


def _doc(doc_id: str, text: str) -> RawDocument:
    return RawDocument(
        doc_id=doc_id,
        source_uri=f"docs/{doc_id}",
        title=doc_id,
        content=text,
        content_hash=compute_sha256(text),
    )


def test_incremental_sync_detects_new_modified_unchanged_and_deleted(tmp_path: Path) -> None:
    tracker = IncrementalSyncTracker(tmp_path / "sync_state.sqlite")
    d1 = _doc("doc_a.md", "Initial runbook content for Spark optimization.")
    d2 = _doc("doc_b.md", "Initial runbook content for Airflow SLA alerting.")

    # Run 1: both docs are new
    plan1 = tracker.compute_sync_plan([d1, d2])
    assert [d.doc_id for d in plan1.new_docs] == ["doc_a.md", "doc_b.md"]
    assert plan1.modified_docs == []
    assert plan1.deleted_doc_ids == []

    tracker.mark_synced(d1, chunk_count=2)
    tracker.mark_synced(d2, chunk_count=1)

    # Run 2: d1 unchanged, d2 modified, d3 added
    d2_updated = _doc("doc_b.md", "Updated runbook with exponential backoff details.")
    d3 = _doc("doc_c.md", "Brand new Snowflake dynamic tables documentation.")
    plan2 = tracker.compute_sync_plan([d1, d2_updated, d3])

    assert [d.doc_id for d in plan2.unchanged_docs] == ["doc_a.md"]
    assert [d.doc_id for d in plan2.modified_docs] == ["doc_b.md"]
    assert [d.doc_id for d in plan2.new_docs] == ["doc_c.md"]
    assert plan2.deleted_doc_ids == []

    tracker.mark_synced(d2_updated, chunk_count=2)
    tracker.mark_synced(d3, chunk_count=1)

    # Run 3: doc_a removed from source
    plan3 = tracker.compute_sync_plan([d2_updated, d3])
    assert plan3.deleted_doc_ids == ["doc_a.md"]
    tracker.mark_deleted(plan3.deleted_doc_ids)

    active = tracker.get_active_hashes()
    assert "doc_a.md" not in active
    assert set(active.keys()) == {"doc_b.md", "doc_c.md"}
