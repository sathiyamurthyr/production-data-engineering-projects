"""Tests for embeddings, atomic chunk replacement, ACL filtering, and hybrid search."""

import math
from pathlib import Path

from src.embeddings.embedder import DeterministicHashEmbedder
from src.models import TextChunk
from src.vector_store.sqlite_vector_store import SQLiteVectorStore, cosine_similarity


def _chunk(chunk_id: str, doc_id: str, idx: int, text: str, acl: str = "engineering") -> TextChunk:
    return TextChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        chunk_index=idx,
        text=text,
        token_count=len(text.split()),
        heading_path="Guide",
        acl_group=acl,
        source_uri=f"docs/{doc_id}",
        content_hash="hash123",
    )


def test_deterministic_hash_embedder_produces_unit_vectors() -> None:
    embedder = DeterministicHashEmbedder(dimensions=64)
    vectors = embedder.embed_texts(["Spark skew salting broadcast join", "Snowflake micro partition"])
    for vec in vectors:
        assert len(vec) == 64
        norm = math.sqrt(sum(v * v for v in vec))
        assert math.isclose(norm, 1.0, rel_tol=1e-4)

    sim_same = cosine_similarity(vectors[0], embedder.embed_query("Spark skew broadcast join"))
    sim_diff = cosine_similarity(vectors[0], vectors[1])
    assert sim_same > sim_diff


def test_vector_store_replaces_stale_chunks_and_enforces_acl_filter(tmp_path: Path) -> None:
    embedder = DeterministicHashEmbedder(dimensions=64)
    store = SQLiteVectorStore(tmp_path / "vec.sqlite")

    c1 = _chunk("doc1::c0", "doc1", 0, "Spark adaptive query execution handles skew joins.", "engineering")
    c2 = _chunk("doc1::c1", "doc1", 1, "Legacy Spark RDD tuning parameter notes.", "engineering")
    c_hr = _chunk("hr1::c0", "hr1", 0, "Executive salary compensation bonus bands restricted.", "hr_admin")

    store.replace_document_chunks("doc1", embedder.embed_chunks([c1, c2]))
    store.replace_document_chunks("hr1", embedder.embed_chunks([c_hr]))
    assert store.count_chunks() == 3

    # Replacing doc1 with 1 chunk must clean up the stale 2nd chunk
    c1_new = _chunk("doc1::c0_v2", "doc1", 0, "Spark AQE dynamically handles skew joins.", "engineering")
    store.replace_document_chunks("doc1", embedder.embed_chunks([c1_new]))
    assert store.count_chunks() == 2

    # Engineering query must NEVER see hr_admin restricted chunk
    q_vec = embedder.embed_query("executive salary compensation bands")
    eng_results = store.search(
        query_text="executive salary compensation bands",
        query_vector=q_vec,
        top_k=5,
        acl_groups=["engineering"],
        mode="hybrid_rrf",
    )
    assert all(r.acl_group == "engineering" for r in eng_results)
    assert all(r.doc_id != "hr1" for r in eng_results)

    # hr_admin query sees hr1
    hr_results = store.search(
        query_text="executive salary compensation bands",
        query_vector=q_vec,
        top_k=5,
        acl_groups=["hr_admin"],
        mode="hybrid_rrf",
    )
    assert hr_results[0].doc_id == "hr1"
