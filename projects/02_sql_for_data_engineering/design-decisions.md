# 🔧 Design Decisions: SQL for Data Engineering

> **Project 02 — Data Engineering Diaries**  
> Explains every major design decision made in the project — from database choice to naming conventions, module structure, SCD implementation, and indexing strategy.

---

## Table of Contents

- [Database Choice: Why SQLite](#database-choice-why-sqlite)
- [ANSI SQL Compatibility Strategy](#ansi-sql-compatibility-strategy)
- [Naming Conventions](#naming-conventions)
- [Module Numbering and Progression](#module-numbering-and-progression)
- [SCD Type 2 Implementation Approach](#scd-type-2-implementation-approach)
- [Index Strategy](#index-strategy)
- [Fact Table Design Decisions](#fact-table-design-decisions)
- [Staging Layer Design](#staging-layer-design)
- [Audit Logging Design](#audit-logging-design)

---

## Database Choice: Why SQLite

### Decision
Use **SQLite 3.35+** as the primary development and CI database.

### Rationale

| Factor | SQLite | PostgreSQL | Snowflake |
|--------|--------|-----------|---------|
| **Setup complexity** | Zero (bundled with Python) | Moderate (install + service) | High (cloud account) |
| **Portability** | Single `.sqlite` file | Server + config | Cloud-only |
| **CI/CD integration** | ✅ In-memory, no service needed | ⚠️ Requires Docker service | ❌ Cost + network |
| **Learning friction** | None | Low | Medium |
| **SQL compatibility** | ~95% ANSI SQL | Full ANSI + extensions | Full ANSI + extensions |
| **Production use** | ❌ Not for large-scale DW | ✅ | ✅ |

### Consequences

- Every SQL file in `queries/` runs on SQLite by default.
- Where SQLite has dialect differences (e.g., no `DATE_TRUNC`, no `GENERATE_SERIES`), comments in each SQL file document the PostgreSQL/Snowflake equivalent.
- The `src/query_runner.py` module uses `sqlite3` from the Python standard library — **zero extra dependencies** for core functionality.
- The pre-built `datasets/warehouse_db.sqlite` lets anyone clone the repo and start querying in under 60 seconds.

### Alternative Considered
Run PostgreSQL via Docker. Rejected because it adds a Docker dependency, a `docker-compose up` step, and network configuration — creating unnecessary friction for the primary goal (learning SQL patterns, not ops).

---

## ANSI SQL Compatibility Strategy

### Decision
Write all SQL in ANSI-compatible syntax. Document dialect-specific alternatives in each file's header comments.

### Implementation

Each SQL module header follows this template:

```sql
-- Module: m25_window_functions.sql
-- Compatible: SQLite 3.35+ | PostgreSQL 14+ | Snowflake | Databricks SQL | Redshift
-- Dialect Note: All window functions below use ANSI SQL syntax and run unmodified
--               on all listed platforms. SQLite added window function support in v3.25.
```

When a query CANNOT be expressed identically across platforms, the file provides both versions:

```sql
-- SQLite: use strftime()
SELECT strftime('%Y-%m', sale_date) AS month FROM fact_sales;

-- PostgreSQL / Snowflake: use DATE_TRUNC()
-- SELECT DATE_TRUNC('month', sale_date::DATE)::TEXT AS month FROM fact_sales;
```

### Key Dialect Differences Documented

| Feature | SQLite | PostgreSQL | Snowflake |
|---------|--------|-----------|---------|
| Date truncation | `strftime('%Y-%m', col)` | `DATE_TRUNC('month', col)` | `DATE_TRUNC('month', col)` |
| String concat | `\|\|` operator | `\|\|` or `CONCAT()` | `\|\|` or `CONCAT()` |
| Boolean | `0/1` INTEGER | `TRUE/FALSE` | `TRUE/FALSE` |
| Auto-increment | `AUTOINCREMENT` | `SERIAL` or `GENERATED ALWAYS` | `AUTOINCREMENT` |
| ILIKE (case-insensitive) | `LIKE` (always case-insensitive) | `ILIKE` | `ILIKE` |
| `RETURNING` clause | v3.35+ | v8.2+ | ❌ not supported |

---

## Naming Conventions

### Decision
Use `snake_case` throughout with object-type prefixes.

### Table Naming

| Prefix | Type | Example | Purpose |
|--------|------|---------|---------|
| `dim_` | Dimension table | `dim_customers` | Reference data, slowly changing |
| `fact_` | Fact table | `fact_sales` | Transactional measures |
| `stg_` | Staging table | `stg_sales_incremental` | Raw landing zone, intermediate |
| `vw_` | View | `vw_monthly_revenue` | Virtual reporting layer |
| `mvw_` | Materialized view | `mvw_product_summary` | Pre-computed aggregations |
| `audit_` / `_log` | Audit table | `audit_logs` | Pipeline observability |

### Column Naming

| Convention | Example | Rationale |
|-----------|---------|-----------|
| Surrogate key = `{table_singular}_key` | `customer_key` | Differentiates from business key |
| Business / natural key = `{entity}_id` | `customer_id` | Maps to source system identifier |
| Date columns = `{event}_date` | `sale_date`, `hire_date` | Clear temporal semantics |
| Timestamp columns = `{event}_at` | `executed_at`, `created_at` | Distinguishes full timestamp from date |
| Boolean flags = `is_{state}` | `is_current`, `is_active` | Reads as true/false predicate |
| Amounts = `{type}_amount` | `gross_amount`, `net_amount` | Avoids ambiguous "amount" alone |
| Status fields = `status` (consistent) | `status = 'COMPLETED'` | Enum-like TEXT with UPPER_CASE values |

### Module File Naming

```
m{NN}_{topic_name}.sql
```
- Two-digit zero-padded number (`m01`, `m25`, `m55`)
- Lowercase `snake_case` topic
- No abbreviations — prefer readability (`m11_joins.sql` not `m11_jn.sql`)

---

## Module Numbering and Progression

### Decision
Use a linear 01–55 numbering with deliberate conceptual progression.

### Progression Design

```
m01–m10   → Foundations (SELECT, WHERE, ORDER BY, aggregates)
             ↓ Must master before moving on
m11–m17   → Multi-table queries (JOINs, set operations)
             ↓ JOINs are the most common interview topic
m18–m29   → Expressions & functions (CASE, NULL, CAST, CTEs, window functions)
             ↓ Window functions are the most powerful analytical tool
m30–m40   → Advanced SQL (views, transactions, ACID, indexes, EXPLAIN)
             ↓ Shift from "writing queries" to "engineering queries"
m41–m46   → Data Warehouse Design (normalization, star/snowflake, fact/dim types)
             ↓ Understand the structures before operating on them
m47–m55   → Data Engineering Patterns (SCD, CDC, incremental load, data quality, ETL)
             ↓ Production patterns: what separates DE from DB users
```

### Rationale
- **Linear progression** avoids forward references — each module only assumes knowledge from prior modules.
- **Two-digit IDs** ensure alphabetical file sort matches logical study order in any file browser or `ls` output.
- **Domain grouping** (m47–m55) puts the most DE-specific content last, after foundational SQL is solid.

---

## SCD Type 2 Implementation Approach

### Decision
Implement SCD Type 2 on `dim_customers` using the "row versioning" pattern with three control columns.

### Schema Design

```sql
CREATE TABLE dim_customers (
    customer_key         INTEGER PRIMARY KEY AUTOINCREMENT,  -- Surrogate key
    customer_id          TEXT NOT NULL UNIQUE,               -- Business / natural key
    first_name           TEXT NOT NULL,
    last_name            TEXT NOT NULL,
    email                TEXT,
    city                 TEXT,
    state                TEXT,
    country              TEXT,
    effective_start_date TEXT NOT NULL,   -- When this version became active
    effective_end_date   TEXT,            -- NULL means currently active
    is_current           INTEGER DEFAULT 1  -- 1 = current, 0 = historical
);
```

### Update Flow

When a customer moves from New York to Chicago:

```sql
-- Step 1: Expire the old record
UPDATE dim_customers
SET effective_end_date = '2026-07-20',
    is_current = 0
WHERE customer_id = 'CUST001'
  AND is_current = 1;

-- Step 2: Insert the new version
INSERT INTO dim_customers (customer_id, first_name, last_name, email, city, state, country,
                           effective_start_date, effective_end_date, is_current)
VALUES ('CUST001', 'Alice', 'Smith', 'alice@example.com',
        'Chicago', 'IL', 'USA', '2026-07-20', NULL, 1);
```

### Why Not SCD Type 1 or 3?

| Type | Approach | When to Use | Limitation |
|------|----------|-------------|-----------|
| **Type 1** | Overwrite old value | History not needed (e.g., typo fix) | Loses all historical values |
| **Type 2** | New row per change | Full history needed ✅ | Requires surrogate keys |
| **Type 3** | Add `prev_` column | Only need "before/after" | Can only track one prior value |

**Type 2 is the default** for production Data Warehouses because it enables point-in-time queries: "What was this customer's address when they made this purchase in 2024?"

---

## Index Strategy

### Decision
Index foreign keys, frequent filter columns, and status/date columns used in WHERE clauses. Avoid over-indexing write-heavy staging tables.

### Recommended Indexes

```sql
-- Foreign key indexes on fact tables (improves JOIN performance)
CREATE INDEX idx_fact_sales_customer_key ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_product_key  ON fact_sales(product_key);

-- Date range filter (most common fact table filter)
CREATE INDEX idx_fact_sales_sale_date    ON fact_sales(sale_date);

-- Status filter (completed vs failed transactions)
CREATE INDEX idx_fact_sales_status       ON fact_sales(status);

-- Composite: date + status (covers the most common analytical query pattern)
CREATE INDEX idx_fact_sales_date_status  ON fact_sales(sale_date, status);

-- Dimension lookup by business key (CDC / SCD lookups)
CREATE INDEX idx_dim_customers_id        ON dim_customers(customer_id);
CREATE INDEX idx_dim_customers_current   ON dim_customers(is_current);

-- Audit log: pipeline name lookup
CREATE INDEX idx_audit_pipeline          ON audit_logs(pipeline_name, executed_at DESC);
```

### Index Decision Matrix

| Index Type | When to Create | When to Avoid |
|-----------|----------------|---------------|
| **B-Tree (default)** | Equality & range filters | Very low cardinality columns (e.g., `status` alone) |
| **Composite** | Multiple columns always filtered together | Columns filtered independently |
| **Partial** | Only a subset of rows queried (e.g., `is_current = 1`) | Full table scans expected |
| **Covering** | Query only needs indexed columns (avoids table lookup) | Wide indexes consume significant storage |

### Index Guidelines
- **Staging tables**: Minimal indexes — they are write-heavy (every ETL run inserts/truncates).
- **Dimension tables**: Index surrogate key (PK auto-indexed), natural key, and `is_current`.
- **Fact tables**: Index all foreign keys + date column + commonly filtered status/type columns.
- **Avoid**: Indexing every column; indexes have write overhead and storage cost.

---

## Fact Table Design Decisions

### Additive Measures Only
All numeric columns in fact tables are **fully additive** — they can be summed across any combination of dimensions without distortion. Non-additive metrics (ratios, percentages) are computed in views, not stored in fact tables.

### Surrogate Key as FK
Fact tables reference dimension tables via **surrogate keys** (`customer_key`, `product_key`), not natural keys. This is a deliberate Data Warehouse convention that:
- Decouples the warehouse from source system key changes
- Allows SCD Type 2 (multiple rows per business entity in dims)
- Maintains referential integrity via FK constraints

### Status Column (UPPER_CASE Values)
All status columns use `UPPER_CASE` string literals: `'COMPLETED'`, `'FAILED'`, `'PENDING'`. This is a deliberate convention for:
- Easy visual identification in query results
- Consistent WHERE clause filtering: `WHERE status = 'COMPLETED'`
- Preventing case-sensitivity bugs across platforms

---

## Staging Layer Design

### Decision
Use a dedicated `stg_` prefix table as the incremental load buffer between source extraction and fact table MERGE.

### Design Principles
1. **Schema mirrors source format** — `stg_sales_incremental` uses `customer_id` (TEXT) and `product_id` (TEXT), matching source system output, NOT surrogate keys.
2. **Staging is truncate-and-reload** — Each pipeline run truncates the staging table and re-loads the delta from the source. No history is retained in staging.
3. **Transformation happens at MERGE time** — The lookup from `customer_id → customer_key` and `product_id → product_key` happens during the INSERT into `fact_sales`, not in staging.

---

## Audit Logging Design

### Decision
Every ETL pipeline run writes one row to `audit_logs` with the operation summary and final status.

### Schema
```sql
CREATE TABLE audit_logs (
    log_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name     TEXT NOT NULL,     -- e.g., 'daily_sales_etl'
    table_name        TEXT NOT NULL,     -- e.g., 'fact_sales'
    records_inserted  INTEGER DEFAULT 0,
    records_updated   INTEGER DEFAULT 0,
    status            TEXT NOT NULL,     -- 'SUCCESS' | 'FAILED' | 'PARTIAL'
    executed_at       TEXT NOT NULL      -- ISO 8601 UTC timestamp
);
```

### Why This Matters
- **High-watermark source** — `MAX(executed_at) WHERE status = 'SUCCESS'` gives the last successful run timestamp, which drives incremental load boundaries.
- **Observability** — Ops teams can query: "Which pipelines failed in the last 24 hours?"
- **SLA tracking** — `executed_at` enables SLA breach detection: "Did the daily ETL complete before 6 AM?"
- **Volume validation** — Sudden drops in `records_inserted` (e.g., 5000 → 0) signal upstream source issues.

---

*See [architecture.md](architecture.md) for the complete schema ER diagram and data flow.*  
*See [performance.md](performance.md) for index strategy and query optimization details.*
