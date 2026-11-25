# Performance & Cost Optimization Guide

## 1. Embedding Token Spend & Cost Controls
- **Incremental CDC Sync:** Only `NEW` and `MODIFIED` documents are embedded (`run2.tokens_embedded == 0` when nothing changes).
- **Near-Duplicate Suppression:** `ContentGuardrails.is_near_duplicate()` uses 3-gram Jaccard similarity (`threshold = 0.85`) to drop boilerplate copies before paying embedding costs.
- **Batching:** `BaseEmbedder.embed_chunks()` groups requests into configurable batches (`batch_size: 16` or `64`), reducing HTTP round-trips by 16x–64x.

## 2. Chunk Size & Retrieval Latency Tradeoffs
- **Smaller chunks (120–200 tokens):** Higher precision per retrieved snippet, lower LLM prompt-token cost at generation time, slightly larger index row count.
- **Larger chunks (400–800 tokens):** Better multi-paragraph continuity, fewer index rows, higher risk of embedding dilution across unrelated subtopics.

## 3. Scaling Beyond Local SQLite
- Up to ~100k chunks: SQLite + indexed `acl_group` / `doc_id` filtering performs well locally.
- 1M–100M+ chunks: Swap `BaseVectorStore` implementation to **PostgreSQL `pgvector` (HNSW + GIN FTS)**, **Qdrant**, or **Databricks Vector Search** with HNSW/IVFPQ approximate nearest neighbor indexing.
