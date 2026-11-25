# Architectural & Design Decisions: dbt Implementation

This document logs the core architectural decisions, technology choices, modeling trade-offs, and engineering rationale for the **dbt (data build tool)** analytics engineering platform.

---

## Decision Log Summary

| ADR ID | Topic | Decision | Status | Rationale |
|--------|-------|----------|--------|-----------|
| **ADR-01** | Transformation Engine | Adopt dbt Core over Custom Python/Airflow SQL | Accepted | Native lineage DAG, standardized testing, Jinja modularity, zero infrastructure lock-in. |
| **ADR-02** | Data Modeling Methodology | Kimball Dimensional Modeling (Star Schema) | Accepted | Separates facts and dimensions; optimized for BI slice-and-dice, clean join paths, efficient warehouse caching. |
| **ADR-03** | Layering Architecture | Staging &rarr; Intermediate &rarr; Marts | Accepted | Prevents DRY violation; isolates raw changes to staging layer; standardizes business logic prior to presentation. |
| **ADR-04** | Incremental Strategy | Merge Strategy (`unique_key`) | Accepted | Prevents duplicate records on re-runs; handles late-arriving updates safely without full table scans. |
| **ADR-05** | Primary Key Design | Hashed Surrogate Keys (`dbt_utils.generate_surrogate_key`) | Accepted | Ensures deterministic, warehouse-agnostic surrogate keys across composite business attributes. |
| **ADR-06** | Data Quality Testing | Dual Strategy (Generic YAML + Custom Singular SQL) | Accepted | Generic tests validate basic constraints (`not_null`, `unique`); singular SQL handles domain business rules. |

---

## Deep-Dive Rationale

### ADR-01: dbt Core vs. Custom Python / Airflow SQL Operators

#### Context
Historically, analytics transformations were orchestrated using custom Python scripts executing raw `psycopg2` or `snowflake-connector` SQL strings, or Airflow `PostgresOperator` nodes executing giant SQL scripts.

#### Problem
- Lack of explicit dependency management: Hand-coded SQL script sequencing in Airflow DAGs lead to fragile pipelines.
- No unified documentation or column-level data lineage.
- Testing requires separate Python validation scripts.
- Boilerplate `CREATE TABLE AS SELECT` code mixed with business logic.

#### Decision
Implement **dbt Core** as the standardized transformation framework.

#### Consequences & Trade-offs
- **Pros**:
  - Declarative dependency management via `ref()` macros.
  - Automated compilation, documentation generation, and visual DAG visualization.
  - Ecosystem of community packages (`dbt_utils`, `dbt_expectations`).
  - Seamless CI/CD state comparisons (Slim CI).
- **Cons**:
  - Transformations are constrained to SQL and Python models (no arbitrary bash or external API calls inside dbt).
  - Requires training data team on Jinja templating and dbt project structure.

---

### ADR-02: Kimball Dimensional Modeling vs. One Big Table (OBT)

#### Context
Data warehouses can store data in wide denormalized tables (One Big Table) or normalized Star-Schema dimensional models (Kimball).

#### Rationale
While OBT offers simplified querying for end-users, it causes significant data redundancy, higher storage costs, update anomalies, and complex maintenance when shared across multiple reporting applications.

```
       [ One Big Table (OBT) ]                      [ Kimball Star-Schema ]
+------------------------------------+        +---------------+     +---------------+
| Order ID | Customer | Prod | Price |        | dim_customers |     | dim_products  |
+------------------------------------+        +-------+-------+     +-------+-------+
| 1001     | Alice    | Shoe | 99.00 |                |                     |
| 1002     | Alice    | Hat  | 25.00 |                v                     v
| 1003     | Bob      | Shoe | 99.00 |        +-------------------------------------+
+------------------------------------+        |             fct_orders              |
                                              +-------------------------------------+
```

#### Decision
Adopt **Kimball Dimensional Modeling**:
- **Facts (`fct_orders`)**: Store measurable quantitative business events (prices, quantities, timestamps).
- **Dimensions (`dim_customers`, `dim_products`)**: Store descriptive context, attributes, and categorizations.

#### Impact
- Faster BI performance due to warehouse column-pruning and dictionary encoding.
- Reusable dimensions shared across multiple fact tables (`fct_orders`, `fct_events`).

---

### ADR-03: Staging -> Intermediate -> Marts Layering Guidelines

#### Context
Organizing dbt models without strict boundaries leads to direct references between raw sources and presentation reports ("spaghetti lineage").

#### Rationale & Design Standard

1. **Staging Models (`stg_*`)**:
   - **Allowed**: `source()`, light renaming, datatype casting, `dbt_utils.generate_surrogate_key()`.
   - **Forbidden**: `ref()`, multi-table joins, `GROUP BY` aggregations.
   - **Materialization**: `view`.

2. **Intermediate Models (`int_*`)**:
   - **Allowed**: `ref('stg_*')`, multi-table joins, business logic CTEs, complex window functions.
   - **Forbidden**: Exposure to BI dashboard tools.
   - **Materialization**: `view` or `ephemeral`.

3. **Marts Models (`fct_*`, `dim_*`, `rpt_*`)**:
   - **Allowed**: `ref('int_*')`, final dimensional formatting, executive rollups.
   - **Materialization**: `table` or `incremental`.

---

### ADR-04: Incremental Materialization Strategy for High-Volume Fact Tables

#### Context
`fct_orders` contains millions of historical transactions. Rebuilding the entire table on every dbt run (`table` materialization) causes query timeouts and unnecessary warehouse cost.

#### Decision
Materialize `fct_orders` as `incremental` using the `merge` strategy:

```sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='merge',
    on_schema_change='append_new_columns'
) }}

select * from {{ ref('int_customer_orders') }}

{% if is_incremental() %}
  where order_date >= (select max(order_date) - interval '3 days' from {{ this }})
{% endif %}
```

#### Rationale for 3-Day Lookback Window
- Accommodates late-arriving transactions or updated payment status without full table scans.
- Uses `unique_key='order_id'` so updated orders overwrite existing records in target table instead of inserting duplicates.

---

### ADR-05: Hashed Surrogate Keys vs. Auto-Incrementing Integers

#### Context
Dimensional modeling requires surrogate primary keys. Data warehouses running distributed queries (Snowflake, Redshift, BigQuery) do not perform well with traditional sequential auto-increment sequence generators (`IDENTITY(1,1)`).

#### Decision
Generate 128-bit MD5 / SHA256 hashed surrogate keys across primary attributes using Jinja macros:
```sql
{{ dbt_utils.generate_surrogate_key(['customer_id', 'email']) }}
```

#### Rationale
- Completely deterministic: Key generation depends strictly on column values, enabling idempotent re-runs.
- Parallelizable across distributed warehouse nodes without coordination locking.
- Portable across PostgreSQL, Snowflake, BigQuery, and Databricks SQL adapters.

---

### ADR-06: Testing Rationale (Generic vs. Singular Tests)

#### Context
Data pipelines require continuous automated validation to prevent bad data from reaching BI dashboards.

#### Rationale & Implementation Strategy
- **Generic Tests (`schema.yml`)**: Used for standard integrity rules (`not_null`, `unique`, `accepted_values`, `relationships`). Low maintenance, declared in YAML.
- **Singular Tests (`tests/*.sql`)**: Used for domain-specific business rules (e.g., `assert_revenue_positive.sql` ensures total order amount is non-negative; `assert_orders_have_customers.sql` asserts referential integrity). SQL queries must return 0 records to pass.
- **`dbt_expectations`**: Leverages Great Expectations assertions natively inside dbt YML configs for statistical validation.
