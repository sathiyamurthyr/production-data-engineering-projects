# Interview Questions: AI / LLM Data Engineering Pipelines (20 Q&As)

### 1. Why shouldn't a RAG pipeline re-embed the entire corpus on every scheduled run?
Embedding APIs charge per token and enforce strict RPM/TPM rate limits. Re-embedding unchanged corporate documents wastes spend and extends pipeline SLAs. Computing a SHA-256 `content_hash` per document and comparing it against a persisted CDC state store (`IncrementalSyncTracker`) ensures only `NEW`, `MODIFIED`, and `DELETED` documents are processed (`0` tokens embedded on unchanged runs).

### 2. What is the "orphan chunk" problem in vector stores, and how do you prevent it?
If a document originally produced 5 chunks (`c0`–`c4`) and after an edit shrinks to 2 chunks (`c0`–`c1`), a naive `UPSERT` overwrites `c0`–`c1` but leaves stale `c2`–`c4` behind. Wrap `DELETE WHERE doc_id = ?` and bulk `INSERT` of the new chunks in an atomic transaction (`replace_document_chunks()`), and delete chunks for deleted source documents via tombstones.

### 3. Why must PII redaction and secret scanning run *before* chunking and embedding?
Vector databases store raw chunk text alongside semantic embeddings. If emails, SSNs, or API keys (`sk-...`, `AKIA...`) are indexed, vector-store backups, similarity queries, or retrieval logs expose sensitive data even if an LLM output filter tries to mask them later. Sanitize PII before chunking and quarantine documents with raw secrets.

### 4. Fixed-size chunking vs. structure-aware chunking — how do you choose?
Fixed-size overlap chunking is simple for uniform transcripts, but severs section headers from bullet lists in technical docs. Structure-aware (`markdown_aware`) chunking splits along heading boundaries first, applies token-bounded sliding windows inside large sections, and prepends `[Parent > Child]` heading paths to every chunk so context survives retrieval.

### 5. Why use Hybrid Search (Vector + Lexical/BM25 with RRF) instead of pure vector search?
Dense embeddings capture semantic paraphrases (*"straggler tasks"* -> *"data skew"*), whereas lexical search nails exact tokens like error codes (`FetchFailedException`), SQL table names (`fact_orders`), or config keys (`TARGET_LAG`). Reciprocal Rank Fusion (`1 / (k + rank_vec) + 1 / (k + rank_lex)`) combines both without fragile score calibration.

### 6. Why is post-filtering ACLs after Top-K retrieval broken in enterprise RAG?
If Top-5 global results belong to a restricted group (`hr_admin`), post-filtering returns 0 results to an `engineering` user even when valid engineering chunks existed at ranks 6–10—and leaks existence via timing/empty responses. Always push `acl_group` filters into the vector store query (`WHERE acl_group IN (...)`) **before** ranking.

### 7. How do you design deterministic chunk IDs for idempotent re-runs?
Derive `chunk_id` from a hash of `(doc_id, chunk_index, chunk_text)` (e.g., `doc_id::c0001::<sha256[:12]>`). Re-running the same document produces identical IDs, preventing duplicate rows on retries.

### 8. How do you handle prompt-injection payloads hidden inside ingested documents?
Run pre-indexing `ContentGuardrails` to flag and quarantine suspicious instruction overrides (e.g., *"ignore all previous instructions"*, `<system>` tags) before chunks enter the RAG index, and treat retrieved chunks as untrusted data inside delimited context blocks at generation time.

### 9. Why use near-duplicate detection (MinHash / Jaccard shingles) before embedding?
Corporate wikis, support tickets, and mirrored runbooks often contain 90%+ identical boilerplate. Dropping near-duplicates (`jaccard_threshold >= 0.85`) cuts embedding spend, reduces index bloat, and prevents Top-K retrieval slots from being filled by 5 copies of the same paragraph.

### 10. How do you size `max_tokens` and `overlap_tokens` for chunking?
Smaller chunks (120–250 tokens) give sharper retrieval precision and lower LLM prompt-token cost; larger chunks (400–800 tokens) preserve multi-paragraph reasoning at the risk of embedding dilution. Keeping `overlap_tokens` around 10–20% of `max_tokens` prevents boundary facts from being split cleanly out of reach.

### 11. How do you handle embedding model upgrades (e.g., switching dimensions or models)?
Vectors from different embedding models live in incompatible vector spaces. Version the `model_name` on every stored chunk, build a shadow collection/index for the new model, run golden-set evaluation (`Recall@K`, `MRR`), and atomically cut over the read alias once metrics meet SLA.

### 12. How do you protect embedding pipelines against API 429 rate limits and transient failures?
Batch chunks (`batch_size: 16–64`) to minimize HTTP round-trips, implement exponential backoff with jitter (`OpenAICompatibleEmbedder`), track token budgets per run, and checkpoint synced documents per batch so a crash at doc 9,000 doesn't re-embed docs 1–8,999.

### 13. How do you evaluate whether a chunking or retrieval tweak actually improved RAG quality?
Maintain a versioned **golden Q&A dataset** (`eval_golden_set.json`) mapping queries + `acl_groups` to `expected_doc_ids`, and measure **Recall@K**, **MRR (Mean Reciprocal Rank)**, and **nDCG@K** automatically in CI (`RAGEvaluator`) before deploying config changes.

### 14. What is the difference between Recall@K, MRR, and nDCG@K in RAG evaluation?
- **Recall@K:** Fraction of expected relevant documents appearing anywhere in the top K results (measures coverage).
- **MRR:** Average of `1 / rank` of the *first* relevant document (measures how high the best match sits).
- **nDCG@K:** Position-discounted cumulative gain rewarding multiple relevant docs appearing at the very top of the ranked list.

### 15. When should you migrate from SQLite/local vector storage to `pgvector`, Qdrant, or Databricks Vector Search?
Local SQLite brute-force cosine search works well up to ~50k–100k chunks. Beyond 100k–100M+ chunks, or when concurrent writes, sub-20ms p99 latency, and HNSW/IVFPQ approximate nearest-neighbor indexing are required, swap the `BaseVectorStore` implementation to `pgvector` (HNSW + GIN FTS), Qdrant, or managed cloud vector search.

### 16. How do you track lineage and observability in an LLM data pipeline?
Emit structured per-run telemetry (`PipelineRunReport` to JSONL/metrics DB) recording `docs_scanned`, `docs_new`, `docs_modified`, `docs_unchanged`, `docs_deleted`, `docs_quarantined`, `tokens_embedded`, `estimated_cost_usd`, and `pii_redactions_total`, and preserve `source_uri` + `heading_path` on every chunk for citation traceability.

### 17. How do you handle unstructured PDFs, tables, and multi-column layouts in production?
Use layout-aware parsers (e.g., Unstructured, Docling, or PyMuPDF) to extract reading-order text and serialize tables into Markdown/JSON rows *before* passing them into `DocumentChunker`, rather than raw character extraction that scrambles columns.

### 18. Why is L2 normalization important for embedding vectors?
When vectors are L2-normalized (`||v||_2 = 1`), cosine similarity equals the dot product (`a . b`), which speeds up vector similarity computation in ANN indexes and avoids norm-skew across differing text lengths.

### 19. How do you prevent stale answers when source documents are deleted from Confluence or S3?
Compute the symmetric difference between active source `doc_id`s and `IncrementalSyncTracker.get_active_hashes()`. Any missing `doc_id` triggers `vector_store.delete_by_doc_ids()` and `sync_tracker.mark_deleted()` so deleted policies disappear immediately.

### 20. How do you structure an end-to-end RAG pipeline so it is testable offline in CI without spending API credits?
Abstract the embedder (`BaseEmbedder`) and vector store (`BaseVectorStore`) behind clean interfaces. Use `DeterministicHashEmbedder` + `SQLiteVectorStore` in unit/integration CI tests to verify chunking, CDC idempotency, PII redaction, ACL isolation, and retrieval evaluation at zero cost.
