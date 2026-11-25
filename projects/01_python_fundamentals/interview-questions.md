# Curated Data Engineering Interview Questions & Answers (20 Q&As)

### Q1: How do you handle deduplication in high-throughput data streams in Python?
**Answer**: Use Python `set()` for O(1) key lookups, or sliding time window state stores when memory is constrained.

### Q2: What is the difference between `list.append()` and Python Generators for ETL?
**Answer**: `list.append()` buffers all records in memory, which leads to OOM crashes for large datasets. Generators yield records on demand, consuming minimal memory.

### Q3: How do you ensure idempotency in file loading pipelines?
**Answer**: Write output to temporary staging files first, and perform an atomic overwrite/rename operation upon completion.

### Q4: Why are `tuples` or `frozen dataclasses` preferred over `dicts` for immutable audit records and data contracts?
**Answer**: Tuples and `@dataclass(frozen=True)` prevent accidental mutation mid-pipeline, enforce explicit field schemas, support hashing (making them usable in sets/dict keys), and reduce memory overhead when paired with `slots=True`.

### Q5: How do you safely flatten deeply nested JSON payloads from REST APIs without triggering `KeyError`?
**Answer**: Use defensive `.get()` chaining with defaults, recursive flattening helpers, or schema validation (`dataclasses` / `pydantic`) to quarantine malformed payloads into a Dead Letter Queue instead of crashing the batch.

### Q6: What is the difference between `DictReader` and raw `csv.reader` when ingesting production CSVs?
**Answer**: `csv.DictReader` maps columns by header name rather than fragile positional indices, making ingestion resilient to upstream column reordering. Always pair it with `newline=""` and explicit `encoding="utf-8"`.

### Q7: How should timestamps and watermarks be handled in Python ETL pipelines?
**Answer**: Always parse into timezone-aware UTC `datetime` objects (`datetime.now(timezone.utc)` or `datetime.fromisoformat(...).astimezone(timezone.utc)`), never naive local timestamps, to avoid DST bugs and skewed incremental watermarks.

### Q8: Why should production pipelines use Python's `logging` module instead of `print()`?
**Answer**: `logging` supports severity levels (`INFO`, `WARNING`, `ERROR`), structured JSON formatting for log aggregators (CloudWatch, Datadog, ELK), rotating file handlers, and central silencing/filtering—whereas `print()` writes unstructured text to stdout without timestamps or severity.

### Q9: How do you implement a reusable `@retry` decorator with exponential backoff for flaky APIs?
**Answer**: Wrap the target function in `functools.wraps`, catch only transient exceptions (e.g., timeouts, HTTP 429/5xx), sleep `base_delay * (2 ** attempt)` plus jitter, and re-raise after `max_retries` so non-transient `400 Bad Request` errors fail fast.

### Q10: Why use context managers (`with` / `@contextmanager`) for database connections and file streams?
**Answer**: Context managers guarantee deterministic cleanup (`close()`, `rollback()` on exception, `commit()` on success) even when an error occurs mid-batch, preventing file-descriptor leaks and dangling database locks.

### Q11: How do you design extensible Extractors and Loaders in Python?
**Answer**: Define Abstract Base Classes (`abc.ABC` with `@abstractmethod`) such as `BaseExtractor` and `BaseLoader`. Pipeline orchestration depends only on the abstract interface (Strategy Pattern), allowing new sources (CSV, REST API, SQLite) to plug in without changing orchestrator logic.

### Q12: How do you mask PII (emails, phone numbers, SSNs) safely in Python before writing logs or analytics outputs?
**Answer**: Apply pre-compiled `re.compile()` regex patterns or deterministic HMAC/SHA-256 hashing with a secret salt (stored in environment variables/Secrets Manager, never hardcoded) so masked identifiers remain joinable without exposing raw PII.

### Q13: How do you handle pagination and rate limits when ingesting from REST APIs?
**Answer**: Loop over cursor/next-page tokens or `offset`/`limit` pages using a generator, respect `Retry-After` headers and HTTP 429 status codes with exponential backoff, and checkpoint the latest cursor so failed runs resume cleanly.

### Q14: Why is `pathlib.Path` preferred over string concatenation or `os.path`?
**Answer**: `pathlib.Path` provides object-oriented, cross-platform path operations (`/` operator, `.mkdir(parents=True, exist_ok=True)`, `.rglob()`) that handle Windows backslashes and POSIX forward slashes uniformly.

### Q15: How do you load 10+ GB CSV files with Pandas without blowing up RAM?
**Answer**: Stream chunks via `pd.read_csv(..., chunksize=50_000)`, restrict columns with `usecols`, specify compact `dtype`s (e.g., `category`, `int32`), or switch to `pyarrow` / Polars / DuckDB / PySpark for out-of-core execution.

### Q16: How do you prevent SQL injection when executing dynamic queries with `sqlite3` or DB drivers?
**Answer**: Always pass runtime values as parameterized placeholders (`?` in `sqlite3`, `%s` in `psycopg`) rather than Python f-strings, and validate dynamic table/column identifiers against an explicit allowlist.

### Q17: Why is strict type hinting (`typing` + `mypy`) valuable in data engineering codebases?
**Answer**: Type hints (`Optional`, `Sequence`, `Dict[str, Any]`, `TypeVar`) catch `None`-handling bugs, mismatched schema contracts, and wrong return types statically in CI before a nightly ETL job fails 2 hours into execution.

### Q18: How do you decouple secrets and environment configs across Dev, Staging, and Prod?
**Answer**: Follow the 12-Factor App pattern: store non-secret config in YAML/JSON files (`configs/`) and inject credentials via environment variables (`os.getenv`) or a Secrets Manager (AWS Secrets Manager / HashiCorp Vault), never committing secrets to Git.

### Q19: How do you unit-test an ETL module that calls an external REST API or database?
**Answer**: Use `pytest` fixtures (`tmp_path` for isolated files/SQLite DBs) and `unittest.mock.patch` / dependency injection to simulate HTTP 200, 429, and 500 responses deterministically with zero network calls in CI.

### Q20: What is the difference between `subprocess.run(..., check=True)` and shell-string execution?
**Answer**: Passing an argument list with `shell=False` and `check=True` prevents command-injection vulnerabilities from untrusted filenames/parameters and ensures non-zero exit codes immediately raise `CalledProcessError` instead of silently failing.
