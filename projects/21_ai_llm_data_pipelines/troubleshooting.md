# Troubleshooting Runbook

## 1. Stale Information Appears After Document Edits or Deletions
- **Cause:** Vector store `UPSERT` updated chunk `0..1`, but an older version of the document had chunk `2..4` that were never deleted.
- **Fix:** Always use `SQLiteVectorStore.replace_document_chunks(doc_id, chunks)` (atomic `DELETE` + `INSERT`) and run `delete_by_doc_ids(plan.deleted_doc_ids)` on every sync cycle.

## 2. Unauthorized Documents Returned to Users
- **Cause:** Filtering by `acl_group` *after* `top_k` retrieval or omitting `acl_groups` in `pipeline.query()`.
- **Fix:** Pass `acl_groups=[...]` to `pipeline.query()`, which executes `WHERE acl_group IN (...)` before scoring.

## 3. Sudden Spike in Embedding API Bills or 429 Rate Limits
- **Cause:** State DB (`rag_pipeline_state.sqlite`) was ephemeral or wiped between runs, forcing full re-ingestion of unchanged docs; or `batch_size` is `1`.
- **Fix:** Persist `state_db_path` in durable storage, increase `batch_size` (e.g. `64`), and verify `docs_unchanged` in `output/pipeline_audit.jsonl`.

## 4. Low Recall@K on Exact Error Codes or Table Names
- **Cause:** Pure dense vector search (`mode="vector"`) smooths over exact identifiers like `FetchFailedException` or `TARGET_LAG`.
- **Fix:** Use `mode="hybrid_rrf"` (default) to combine semantic cosine ranking with lexical keyword ranking.
