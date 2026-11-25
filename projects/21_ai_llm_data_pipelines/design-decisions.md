# Design Decisions: AI / LLM Data Engineering Pipelines

## 1. SHA-256 Incremental Sync Before Embedding
- **Decision:** Compute `content_hash` at ingestion and check `IncrementalSyncTracker` before sanitizing, chunking, or calling embedding APIs.
- **Rationale:** Embedding APIs charge per token and enforce strict RPM/TPM rate limits. Re-embedding unchanged corporate wikis on daily runs wastes budget and triggers 429 throttling.

## 2. Pre-Embedding PII Redaction Over Post-Retrieval Filtering
- **Decision:** Redact emails, phone numbers, SSNs, credit cards, and raw API keys *before* chunking and vectorization.
- **Rationale:** Once text is embedded and persisted into a vector database, sensitive values live in chunk payloads and semantic neighborhoods. Quarantining documents with raw API credentials (`sk-...`, `AKIA...`) prevents secret sprawl.

## 3. Markdown-Aware Chunking With Heading Provenance
- **Decision:** Split on Markdown headings first, then apply token-bounded sliding windows with overlap, prepending `[Parent > Child]` heading context to every chunk.
- **Rationale:** Bare fixed-size chunking severs section titles from bullet lists, causing chunks like *"Enable AQE and broadcast joins"* to lose what system they apply to.

## 4. Hybrid Retrieval via Reciprocal Rank Fusion (RRF)
- **Decision:** Combine dense cosine similarity and lexical overlap using `1 / (k + rank_vec) + 1 / (k + rank_lex)` (`k = 60`).
- **Rationale:** Dense embeddings capture semantic phrasing (*"straggler tasks"* -> *"data skew"*), while lexical matching nails exact error codes (`OutOfMemoryError`, `TARGET_LAG`, `faq_kafka_dlq`). RRF fuses both without brittle score normalization.

## 5. Strategy Abstraction for Embedders & Vector Stores
- **Decision:** Define `BaseEmbedder` and `BaseVectorStore` ABCs with offline `DeterministicHashEmbedder` + `SQLiteVectorStore` defaults alongside `OpenAICompatibleEmbedder`.
- **Rationale:** Allows deterministic, zero-cost CI testing while keeping production swaps to `pgvector`, Qdrant, or Databricks Vector Search isolated behind one interface.
