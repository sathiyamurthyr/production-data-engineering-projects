# 🏛️ Architecture: SQL for Data Engineering Warehouse

> **Project 02 — Data Engineering Diaries**  
> Architecture document for the enterprise data warehouse used across all 55 SQL modules.

---

## Table of Contents

- [Overview](#overview)
- [Warehouse Schema ER Diagram](#warehouse-schema-er-diagram)
- [Layer Architecture](#layer-architecture)
- [Data Flow Diagram](#data-flow-diagram)
- [Star Schema vs Snowflake Schema](#star-schema-vs-snowflake-schema)
- [Table Descriptions](#table-descriptions)
- [Schema Design Rationale](#schema-design-rationale)

---

## Overview

The `warehouse_db` implements a **star schema** modeled after a mid-size B2B/B2C e-commerce operation. The schema is intentionally multi-domain to allow SQL exercises spanning:

- **Retail analytics** (fact_sales, dim_products, dim_customers)
- **Order management** (fact_orders, fact_payments)
- **Finance / AR** (fact_invoices)
- **Inventory management** (fact_inventory)
- **Healthcare analytics** (healthcare_claims)
- **Banking analytics** (banking_transactions)
- **IoT / Streaming** (iot_sensor_data)
- **ETL operations** (stg_sales_incremental, audit_logs)

This breadth ensures that SQL patterns learned here — window functions, CTEs, SCDs, incremental loading — translate directly to real production environments.

---

## Warehouse Schema ER Diagram

```mermaid
erDiagram
    dim_customers {
        int customer_key PK
        text customer_id UK
        text first_name
        text last_name
        text email
        text city
        text state
        text country
        text effective_start_date
        text effective_end_date
        int is_current
    }

    dim_products {
        int product_key PK
        text product_id UK
        text product_name
        text category
        text subcategory
        real unit_price
        real cost_price
    }

    dim_employees {
        int employee_id PK
        text first_name
        text last_name
        text email
        int department_id FK
        real salary
        int manager_id FK
        text hire_date
    }

    dim_departments {
        int department_id PK
        text department_name
        text manager_name
        text location
    }

    fact_sales {
        int sales_id PK
        text transaction_id UK
        int customer_key FK
        int product_key FK
        text sale_date
        int quantity
        real gross_amount
        real discount_amount
        real net_amount
        text status
    }

    fact_orders {
        int order_id PK
        text order_number UK
        int customer_key FK
        text order_date
        text order_status
        real total_amount
    }

    fact_payments {
        int payment_id PK
        text payment_reference UK
        int order_id FK
        text payment_date
        text payment_method
        real payment_amount
        text status
    }

    fact_invoices {
        int invoice_id PK
        text invoice_number UK
        int customer_key FK
        text invoice_date
        text due_date
        real invoice_amount
        real paid_amount
        text status
    }

    fact_inventory {
        int inventory_id PK
        int product_key FK
        text warehouse_location
        int stock_quantity
        int reorder_level
        text last_updated
    }

    audit_logs {
        int log_id PK
        text pipeline_name
        text table_name
        int records_inserted
        int records_updated
        text status
        text executed_at
    }

    stg_sales_incremental {
        text transaction_id PK
        text customer_id
        text product_id
        text sale_date
        int quantity
        real amount
        text status
    }

    dim_customers ||--o{ fact_sales : "customer_key"
    dim_products ||--o{ fact_sales : "product_key"
    dim_customers ||--o{ fact_orders : "customer_key"
    fact_orders ||--o{ fact_payments : "order_id"
    dim_customers ||--o{ fact_invoices : "customer_key"
    dim_products ||--o{ fact_inventory : "product_key"
    dim_departments ||--o{ dim_employees : "department_id"
```

---

## Layer Architecture

The warehouse uses a **three-tier medallion-inspired architecture**:

```mermaid
flowchart LR
    subgraph L1["🥉 Bronze — Raw / Staging"]
        stg[stg_sales_incremental]
        raw[Raw CSV ingestion]
    end

    subgraph L2["🥈 Silver — Cleansed / Warehouse"]
        dims["Dimension Tables\ndim_customers\ndim_products\ndim_employees\ndim_departments"]
        facts["Fact Tables\nfact_sales\nfact_orders\nfact_payments\nfact_invoices\nfact_inventory"]
    end

    subgraph L3["🥇 Gold — Aggregated / Reporting"]
        views["Views & Materialized Views\nvw_monthly_revenue\nvw_customer_ltv\nvw_product_margin"]
        reports["BI Tools\nDashboards\nAd-hoc Queries"]
    end

    L1 --> L2 --> L3
```

### Layer Descriptions

| Layer | Tables | Role | SQL Patterns |
|-------|--------|------|-------------|
| **Bronze (Raw)** | `stg_*` | Accept raw source data as-is; no transformation | INSERT, COPY |
| **Silver (Warehouse)** | `dim_*`, `fact_*` | Cleansed, typed, validated, historical tracking | MERGE, SCD Type 2, incremental load |
| **Gold (Reporting)** | Views, MVs | Business-ready aggregations, KPIs | CTEs, Window Functions, GROUP BY |

---

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant SRC as Source System
    participant STG as Staging Layer
    participant DIM as Dimension Tables
    participant FACT as Fact Tables
    participant AUD as audit_logs

    SRC->>STG: 1. Extract raw records (CDC/bulk)
    STG->>STG: 2. Validate: null checks, format checks
    STG->>DIM: 3. Upsert dimensions (SCD Type 2)
    STG->>FACT: 4. MERGE facts (dedup + upsert)
    FACT->>AUD: 5. Write audit log (records_in, records_upd, status)
    AUD-->>SRC: 6. Signal pipeline success/failure
```

**Incremental Load Flow (m49):**

```mermaid
flowchart TD
    A[Read HIGH_WATERMARK from audit_logs] --> B[Extract records WHERE sale_date > watermark]
    B --> C[Load into stg_sales_incremental]
    C --> D{MERGE into fact_sales}
    D -- "Matched = UPDATE" --> E[Update existing record]
    D -- "Not Matched = INSERT" --> F[Insert new record]
    E --> G[Update HIGH_WATERMARK in audit_logs]
    F --> G
    G --> H[Write audit_logs entry: SUCCESS / FAILED]
```

---

## Star Schema vs Snowflake Schema

Both schemas are implemented in this project (`m43`, `m44`). Here is a direct comparison:

```mermaid
graph TB
    subgraph STAR["⭐ Star Schema"]
        direction TB
        FS[fact_sales] --> DC1[dim_customers\ncity, state, country embedded]
        FS --> DP1[dim_products\ncategory, subcategory embedded]
    end

    subgraph SNOW["❄️ Snowflake Schema"]
        direction TB
        FS2[fact_sales] --> DC2[dim_customers]
        DC2 --> DG[dim_geography\ncity → state → country]
        FS2 --> DP2[dim_products]
        DP2 --> DC3[dim_categories]
        DC3 --> DSC[dim_subcategories]
    end
```

| Dimension | Star Schema | Snowflake Schema |
|-----------|-------------|-----------------|
| **Structure** | Denormalized dims (flat) | Normalized dims (hierarchical) |
| **Query Speed** | ⚡ Faster (fewer JOINs) | 🐌 Slower (more JOINs) |
| **Storage** | More (redundant data) | Less (normalized) |
| **Maintenance** | Simpler | Complex |
| **Use Case** | Analytics / BI dashboards | OLTP-adjacent, strict normalization |
| **Industry Preference** | ✅ Default choice for DW | Used when storage cost is primary concern |

**Recommendation:** Use **Star Schema** for analytics workloads. The JOIN overhead in Snowflake schema degrades performance at billion-row scale with no meaningful benefit in modern columnar warehouses.

---

## Table Descriptions

### dim_customers
Implements **SCD Type 2** with `effective_start_date`, `effective_end_date`, and `is_current` columns. When a customer's address changes, the old row gets `is_current = 0` and `effective_end_date` set; a new row is inserted with `is_current = 1`.

**Key Columns:**
- `customer_key` — Surrogate key (auto-increment integer)
- `customer_id` — Natural/business key (e.g., 'CUST001')
- `is_current` — 1 = active record, 0 = historical

### dim_products
Product catalog with category hierarchy embedded (star schema). `product_key` is the surrogate key; `product_id` is the business key.

### fact_sales
Primary revenue fact table. Contains additive measures (`gross_amount`, `discount_amount`, `net_amount`, `quantity`) that can be summed across any dimension. Uses surrogate keys from dimension tables for joins.

### audit_logs
Records every ETL pipeline execution. Used in m49 (incremental loading) as the HIGH_WATERMARK store and in m53 (audit tables) for pipeline observability.

### stg_sales_incremental
The staging buffer for incremental sales loads. Records land here from the source system and are then MERGEd into `fact_sales` using the patterns demonstrated in m49 and m54.

---

## Schema Design Rationale

1. **Surrogate keys over natural keys** — All dimension tables use auto-increment integer surrogate keys as the join key to fact tables. This insulates the warehouse from changes in source system key formats.

2. **Separate customer_id as business key** — `customer_id` (TEXT, UNIQUE) is preserved alongside `customer_key` (INTEGER PK) so that source-system lookups remain possible without needing to know the surrogate key.

3. **SCD Type 2 on dim_customers** — Only `dim_customers` has SCD Type 2 columns because customer attributes (address, tier) commonly change over time and historical accuracy matters for cohort analysis.

4. **Additive measures in fact tables** — All numeric columns in fact tables (`gross_amount`, `net_amount`, `quantity`) are fully additive — they can be summed across all dimensions without distortion.

5. **TEXT for dates in SQLite** — SQLite has no native DATE type. Dates are stored as ISO 8601 TEXT (`'2026-07-20'`) for portability. Date functions like `strftime` work correctly on this format. PostgreSQL/Snowflake versions use native DATE type.

---

*See [design-decisions.md](design-decisions.md) for the rationale behind each architectural choice.*
