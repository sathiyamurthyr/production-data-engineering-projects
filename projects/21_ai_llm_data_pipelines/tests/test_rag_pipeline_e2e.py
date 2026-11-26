"""End-to-end integration tests for the AI / LLM RAG Data Pipeline."""

from pathlib import Path
import shutil
import yaml

from src.pipeline.evaluator import RAGEvaluator
from src.pipeline.rag_pipeline import RAGIngestionPipeline


def test_end_to_end_rag_pipeline_idempotency_acl_and_evaluation(tmp_path: Path) -> None:
    project_dir = Path(__file__).resolve().parent.parent
    docs_copy = tmp_path / "docs"
    shutil.copytree(project_dir / "sample-data" / "docs", docs_copy)

    with (project_dir / "configs" / "pipeline_config.yaml").open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    cfg["pipeline"]["state_db_path"] = str(tmp_path / "output" / "state.sqlite")
    cfg["pipeline"]["audit_log_path"] = str(tmp_path / "output" / "audit.jsonl")
    cfg["pipeline"]["quarantine_path"] = str(tmp_path / "output" / "quarantine.jsonl")

    pipeline = RAGIngestionPipeline(cfg, base_dir=tmp_path)

    # 1. Initial full ingestion
    run1 = pipeline.run(docs_copy)
    assert run1.status == "SUCCESS"
    assert run1.docs_scanned == 6  # 3 md + 3 jsonl records
    assert run1.docs_new == 6
    assert run1.chunks_upserted > 0
    assert run1.pii_redactions_total >= 2  # email + phone redacted in spark_skew_playbook.md

    # Verify PII was redacted before reaching the vector store
    skew_hits = pipeline.query(
        "Spark OutOfMemoryError oncall escalation", top_k=3, acl_groups=["engineering"]
    )
    assert any(r.doc_id == "spark_skew_playbook.md" for r in skew_hits)
    assert all("oncall-de@company.com" not in r.text for r in skew_hits)
    assert all("415-555-0199" not in r.text for r in skew_hits)

    # Verify restricted HR doc is filtered out for engineering ACL
    hr_hits = pipeline.query("executive compensation salary bands", top_k=5, acl_groups=["engineering"])
    assert all(r.doc_id != "faq_hr_compensation" for r in hr_hits)

    # 2. Second run with unchanged docs should embed 0 tokens
    run2 = pipeline.run(docs_copy)
    assert run2.docs_unchanged == 6
    assert run2.docs_new == 0
    assert run2.docs_modified == 0
    assert run2.tokens_embedded == 0
    assert run2.estimated_cost_usd == 0.0

    # 3. Evaluate retrieval quality against golden benchmark
    evaluator = RAGEvaluator(pipeline.embedder, pipeline.vector_store)
    summary = evaluator.evaluate_file(
        project_dir / "sample-data" / "eval_golden_set.json",
        top_k=3,
        mode="hybrid_rrf",
    )
    assert summary.total_queries == 4
    assert summary.recall_at_k >= 0.75
    assert summary.mrr >= 0.75
