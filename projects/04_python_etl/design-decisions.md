# Architectural & Design Decisions

This document outlines key engineering choices, trade-offs, and design rationale for the **Python Modular ETL Framework** (`04_python_etl`) built by **Sathiya Murthy**.

---

## 1. Core Framework Rationale: Pandas vs PySpark vs Polars

### Decision: Pandas with PyArrow Engine
For small-to-medium enterprise workloads (datasets up to 10–50 GB per worker node), **Pandas (v2.0+) coupled with PyArrow** was chosen over PySpark or Polars.

| Feature / Criteria | Pandas + PyArrow | PySpark | Polars |
| :--- | :--- | :--- | :--- |
| **Execution Overhead** | Ultra-low local footprint | High (JVM, Driver/Executor setup) | Low memory footprint |
| **Development Velocity** | Standard Python API | Complex distributed debugging | Modern Rust-backed API |
| **Columnar Parquet I/O** | Native PyArrow engine C-bindings | Native Spark Parquet I/O | Native Arrow format |
| **Use Case Fit** | Single-node production microservices, AWS Lambda, Airflow operators | Multi-terabyte distributed data lakes | High-performance single-node streaming |

**Rationale**: Pandas 2.0 PyArrow backend eliminates historical memory fragmentation issues while keeping the deployment package lightweight and dependency-minimal for containerized execution.

---

## 2. Extraction Design Decisions

### 2.1 API Extractor: Synchronous with Exponential Backoff vs Async (aiohttp)
- **Decision**: Synchronous `requests` library paired with manual exponential backoff retry loops.
- **Trade-off**: Asynchronous I/O (`aiohttp`/`asyncio`) provides higher throughput when making thousands of concurrent API requests. However, synchronous extraction with structured retries simplifies debugging, thread safety, and Airflow task isolation.
- **Mock Fallback**: Included a static `mock_response` dictionary configuration option allowing seamless local offline execution and reliable automated unit test suites without hitting external rate limits.

### 2.2 Memory-Efficient File Ingestion: Streaming Chunks vs Full Ingestion
- **Decision**: Implemented `extract_chunks()` generator on `CSVExtractor` alongside standard `extract()`.
- **Rationale**: Datasets exceeding RAM constraints can be processed in streaming mini-batches (`chunksize=1000`), preventing Out-Of-Memory (OOM) kernel panics.

---

## 3. Transformation & Data Quality Strategy

### 3.1 Error Quarantine Strategy: Dead Letter Queue (DLQ) vs Hard Exception
- **Decision**: Route invalid records to a Dead Letter Queue (DLQ) JSON file while allowing clean records to complete the pipeline.
- **Trade-off**: 
  - *Hard Exception (Fail Fast)*: Immediately stops execution when bad data is encountered. Ideal for strict financial ledger pipelines, but leads to pipeline fragility when third-party source schemas drift.
  - *Dead Letter Queue (DLQ)*: Quarantines malformed records alongside explicit `rejection_reasons` for asynchronous auditing, allowing valid business transactions to load without downtime.

### 3.2 Dynamic Header Normalization
- **Decision**: Standardize raw headers to lowercase `snake_case` using regular expressions (`re.sub(r"[^\w]+", "_", col.strip().lower())`).
- **Rationale**: Upstream sources frequently change header casing (e.g., `Customer ID`, `Customer_Id`, `CUSTOMER_ID`). Regularized snake_case prevents downstream SQL or Parquet column lookup failures.

---

## 4. Storage & Loading Drivers

### 4.1 Storage Formats: Columnar Parquet vs Delimited CSV
- **Decision**: Default analytical load target is compressed Parquet (`snappy` codec).
- **Comparison**:
  - **Parquet**: 5x–10x smaller file size on disk due to dictionary & run-length encoding; drastically faster query performance in Snowflake/Athena due to column projection pushdown.
  - **CSV**: Human-readable fallback target for quick reporting exports and legacy integration endpoints.

### 4.2 Database Access: SQLAlchemy Engine with Core Transactions
- **Decision**: Use `sqlalchemy.create_engine` with `engine.begin()` context manager.
- **Rationale**: `engine.begin()` automatically commits the SQL transaction on success or rolls back on exception, preserving Database ACID integrity.

---

## 5. Summary Matrix of Design Choices

| Architectural Requirement | Chosen Strategy | Benefit |
| :--- | :--- | :--- |
| Config Management | YAML via `PipelineConfig` | Separates code from deployment environment parameters |
| Logging | Custom `JSONLogFormatter` | Enables native ingestion into ELK/Datadog log aggregators |
| Storage Integrity | Temporary write + Atomic OS move | Prevents partial or corrupt dataset writes |
| Extensibility | Abstract Base Classes (`ABC`) | Enforces standard interface contract across developers |
