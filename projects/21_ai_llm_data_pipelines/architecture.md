# Architecture: AI / LLM Data Engineering Pipelines

## 1. Core Principle: Treat RAG Ingestion Like Medallion ETL

Most LLM prototypes fail in production because teams treat document indexing as a one-off script rather than an **incremental, observable, governed data pipeline**:

| Layer | Equivalent in Medallion | Responsibility in Project 21 |
|---|---|---|
| **Bronze (Raw Ingestion)** | Raw landing zone | `DocumentLoader` ingests `.md`, `.txt`, `.jsonl`, `.csv` with `doc_id`, `source_uri`, `acl_group`, and SHA-256 `content_hash`. |
| **CDC State Plane** | Watermark / Delta log | `IncrementalSyncTracker` compares incoming hashes against SQLite state to classify `NEW`, `MODIFIED`, `UNCHANGED`, and `DELETED` documents. |
| **Silver (Quality & Chunking)** | Cleansed & conformed | `PIISanitizer` redacts PII/secrets; `ContentGuardrails` blocks prompt injections and near-duplicates; `DocumentChunker` preserves heading hierarchy. |
| **Gold (Vector Index)** | Serving mart | `SQLiteVectorStore` atomically replaces chunks per `doc_id` and serves ACL-filtered hybrid (vector + lexical RRF) retrieval. |
| **Observability & Eval** | Data quality & SLAs | `RAGIngestionPipeline` writes per-run JSONL audit telemetry & token cost; `RAGEvaluator` computes `Recall@K`, `MRR`, and `nDCG@K`. |

## 2. Atomic Document Replacement

When a document is edited and shrinks from 5 chunks to 2 chunks, naive `UPSERT` leaves 3 stale orphan chunks in the vector store. `SQLiteVectorStore.replace_document_chunks()` wraps `DELETE FROM vector_chunks WHERE doc_id = ?` + `INSERT` in a single transaction so stale chunks never contaminate retrieval.

## 3. Enterprise ACL Pre-Filtering

Access control (`acl_group`) is enforced **inside the vector store query (`WHERE acl_group IN (...)`) before ranking**, never as post-filtering after `top_k` selection (which causes empty results or authorization leaks).
