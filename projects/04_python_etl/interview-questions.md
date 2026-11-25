# Python ETL Pipelines - Data Engineering Interview Questions & Answers

This document features technical interview questions, deep-dive answers, code snippets, and architectural explanations for **Python Modular ETL Frameworks**, curated for the **Data Engineering Diaries** series by **Sathiya Murthy**.

---

## Question 1: How do you design an ETL framework in Python to ensure high modularity and extensibility?

### **Answer**:
To achieve high modularity and extensibility, an enterprise ETL framework should apply Object-Oriented Design principles (specifically the **Strategy Pattern** and **Dependency Inversion Principle**):
1. **Abstract Base Classes (ABCs)**: Define standard interface contracts for each pipeline phase:
   - `BaseExtractor.extract(self) -> pd.DataFrame`
   - `BaseTransformer.transform(self, df: pd.DataFrame) -> pd.DataFrame`
   - `BaseLoader.load(self, df: pd.DataFrame) -> bool`
2. **Polymorphic Instantiation**: The pipeline orchestrator dynamically instantiates concrete implementations (`CSVExtractor`, `JSONExtractor`, `ParquetLoader`) based on configuration settings without hardcoding source or target dependencies.
3. **Decoupled Configuration**: All parameters (file paths, connection strings, thresholds, batch sizes) live outside source code in YAML files parsed by `PipelineConfig`.

---

## Question 2: How do you handle schema drift in Python data pipelines?

### **Answer**:
Schema drift occurs when upstream data sources add, drop, rename, or alter column data types. To handle schema drift cleanly:
1. **Header Normalization**: Convert raw column names to standardized lowercase `snake_case` stripping special characters using regular expressions.
2. **Schema Drift Audit**: Compare incoming DataFrame columns against expected schema definitions using a helper like `validate_schema(df, expected_schema, allow_extra_columns=True)`.
3. **Safe Type Casting**: Perform coercing type casts (e.g. `pd.to_numeric(..., errors="coerce")`) to prevent breaking exceptions on dirty data.
4. **Dead Letter Queue Routing**: Quarantine rows failing critical schema constraints into a DLQ JSON artifact while allowing valid rows to proceed.

---

## Question 3: What is Idempotency in ETL pipelines, and how do you enforce it in Python?

### **Answer**:
An ETL pipeline is **idempotent** if running it multiple times on the same input data produces the exact same state in the target data warehouse without creating duplicate records or corrupted states.

### **Enforcement Strategies**:
1. **Database Loaders**: Use transactional table replacement (`if_exists="replace"`) for dimensional lookup tables, or perform SQL `UPSERT` / `MERGE INTO` operations using composite primary key deduplication.
2. **File Loaders**: Use atomic file write patterns (`safe_write_json`) where data is written to temporary files and renamed atomically over target paths, preventing partial state writes.
3. **Partitioned Data Lakes**: Overwrite specific date partition subdirectories (e.g., `year=2023/month=09/day=01/`) rather than appending to dynamic folders.

---

## Question 4: How do you process large flat files (e.g. 50 GB CSV) in Python without running out of RAM?

### **Answer**:
Loading a 50 GB CSV into a single Pandas DataFrame using `pd.read_csv()` requires ~150 GB of RAM due to object overhead. Solutions include:
1. **Streaming Chunks**: Use `pd.read_csv(file_path, chunksize=10000)` generator iterators to stream and process fixed-size batches sequentially.
2. **PyArrow Engine**: Use `engine="pyarrow"` in Pandas 2.0 to load data directly into Apache Arrow columnar memory format with minimal overhead.
3. **Column Projection**: Pass `usecols=['id', 'amount']` to read only required columns into memory.
4. **Distributed Execution**: Transition to PySpark or Polars lazy evaluation frames for distributed datasets.

---

## Question 5: Why use Parquet format over CSV for analytical data warehousing?

### **Answer**:

| Feature | Apache Parquet | CSV File |
| :--- | :--- | :--- |
| **Storage Structure** | Binary Columnar | Plain Text Row-Oriented |
| **Compression** | High (Snappy, ZSTD) with dictionary encoding | Low / Uncompressed |
| **Query Performance** | Fast (reads only projected query columns) | Slow (must scan entire row text) |
| **Schema Preservation** | Embedded schema & data types | No type metadata (all strings) |
| **Pushdown Predicates** | Supported (filters metadata blocks) | Not supported |

---

## Question 6: How do you implement robust, production-grade unit testing for ETL pipelines?

### **Answer**:
1. **Isolated Test Fixtures**: Use `pytest` `tmp_path` fixtures to construct temporary input files (CSV, JSON) and SQLite databases for test runs.
2. **Component Isolation**: Test Extractors, Transformers, and Loaders independently before running integration tests on `ETLPipeline`.
3. **Mock External Network Calls**: Use mock dictionaries (`mock_response`) or `unittest.mock.patch` for `APIExtractor` to prevent network dependencies in CI/CD pipelines.
4. **Assertion Assertiveness**: Verify output row counts, specific column values, file existence, and expected exception raises (`pytest.raises(ExtractionError)`).

```python
def test_csv_extractor_missing_file():
    extractor = CSVExtractor({"path": "missing.csv"})
    with pytest.raises(ExtractionError):
        extractor.extract()
```


---

## Question 7: How do you design a Dead Letter Queue (DLQ) in a Python ETL pipeline without halting valid records?

### **Answer**:
Separate record-level validation failures from fatal infrastructure errors. When `DataValidator` rejects a row (e.g., invalid email regex or negative order amount), attach the raw payload, rule name, timestamp, and `run_id`, append it to `output/dead_letter_queue.json`, and allow valid rows to continue to the loader. Alert ops if the DLQ ratio exceeds an SLA threshold (e.g., > 5%).

---

## Question 8: How do you implement incremental watermark extraction in Python ETL?

### **Answer**:
Persist the high-watermark (`max(updated_at)` or `max(id)`) in an audit state table after a successful load. On the next run, pass `WHERE updated_at > :last_watermark` (with a small overlap window plus downstream deduplication/upsert to handle late-arriving transactions) and advance the watermark only after the target commit succeeds.

---

## Question 9: Why should ETL pipelines use exponential backoff with jitter when calling external REST APIs?

### **Answer**:
Fixed-interval retries can cause a thundering-herd spike against a struggling API. Exponential backoff (`base * 2^attempt`) with random jitter spreads retry traffic over time, honors `Retry-After` headers on HTTP 429/503 responses, and avoids retrying permanent 4xx client errors (`400`, `401`, `404`).

---

## Question 10: What is the difference between `yield` streaming and batching (`itertools.batched`) in ETL?

### **Answer**:
Yielding one record at a time minimizes RAM but causes excessive network round-trips if loaded row-by-row to a database. Combining a generator extractor with fixed-size micro-batches (`1,000–10,000` rows via `itertools.batched` in Python 3.12+) gives bounded memory **and** high-throughput bulk `executemany()` / Parquet writes.

---

## Question 11: How do you emit structured observability logs from a Python ETL orchestrator?

### **Answer**:
Configure a JSON formatter on Python's `logging` module emitting `timestamp`, `level`, `pipeline_name`, `run_id`, `stage`, `rows_in`, `rows_out`, `dlq_count`, and `duration_ms`. Structured JSON logs integrate directly with CloudWatch Logs Insights, Datadog, and ELK dashboards.

---

## Question 12: How do you prevent partial/corrupt Parquet or JSON files if an ETL job crashes mid-write?

### **Answer**:
Write to a temporary staging path (`file.parquet.tmp`) on the same filesystem/bucket prefix, flush and verify row counts, then atomically rename (`os.replace()`) to the final target path. Downstream consumers never observe half-written files.

---

## Question 13: When should you replace Pandas with Polars or DuckDB inside a single-node Python ETL job?

### **Answer**:
Switch to **Polars** or **DuckDB** when datasets reach 2–50 GB on a single machine, where Pandas hits memory amplification (3x–10x CSV size) and single-core bottlenecks. Polars and DuckDB execute multi-threaded columnar Arrow/vectorized plans out-of-core without spinning up a Spark cluster.

---

## Question 14: How do you manage SQLite/PostgreSQL connection pooling and transaction boundaries in Python loaders?

### **Answer**:
Use SQLAlchemy's `Engine` with configured `pool_size`, `max_overflow`, and `pool_pre_ping=True`, and wrap each batch load in `with engine.begin() as conn:` so the entire batch either commits atomically or rolls back cleanly on failure.

---

## Question 15: How do you handle timezone normalization across heterogeneous CSV, JSON, and API sources?

### **Answer**:
Parse incoming timestamps using explicit formats or ISO-8601 parsers, attach or convert source timezones to **UTC** immediately in the Bronze/Silver cleaner, and store normalized ISO-8601 UTC strings (`2026-11-25T15:00:00Z`) or UTC `TIMESTAMP` columns everywhere downstream.

---

## Question 16: How do you decouple environment-specific ETL settings (Dev/Staging/Prod) safely?

### **Answer**:
Keep structural defaults (`batch_size`, `chunk_size`, schema rules) in versioned YAML files (`configs/pipeline_config.yaml`), override environment endpoints via `ENV` variables (`os.getenv`), and pull credentials from AWS Secrets Manager / Azure Key Vault at runtime.

---

## Question 17: What is the difference between soft-delete tombstones and hard deletes in ETL loads?

### **Answer**:
Hard deletes (`DELETE FROM ...`) permanently remove rows, erasing audit history. Soft-delete tombstones set `is_deleted = TRUE` and `deleted_at = UTC_NOW()`, preserving historical lineage and allowing downstream incremental consumers to propagate deletions.

---

## Question 18: How do you prevent memory leaks in long-running Python ETL worker processes?

### **Answer**:
Avoid accumulating processed DataFrames in module-level lists/caches, close file handles and DB cursors via context managers, release large intermediate DataFrames explicitly when chaining stages, and run periodic memory profiling (`tracemalloc`).

---

## Question 19: How do you validate referential integrity in a Python ETL pipeline before loading fact tables?

### **Answer**:
Fetch active surrogate/natural keys from dimension tables (or broadcast sets for small dimensions), perform a set-difference / left-anti join against incoming fact rows, and route unmatched foreign keys to a late-arriving-dimension quarantine queue or assign an inferred placeholder member.

---

## Question 20: How do you benchmark and profile bottlenecks across Extract, Transform, and Load stages?

### **Answer**:
Instrument each stage with a `@timeit` / context timer logging wall time, CPU time, and rows/sec, and run `cProfile` or `py-spy` on slow transforms. Typically 80% of time is spent in unvectorized `df.apply()` loops (fix with vectorized NumPy/Arrow ops) or row-by-row SQL inserts (fix with bulk `COPY` / `executemany`).
