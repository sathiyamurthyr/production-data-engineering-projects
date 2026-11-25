# Architecture Design: dbt Analytics Engineering Engine

## Executive Architecture Summary

This document details the architectural design and structural patterns implemented in the enterprise **dbt (data build tool)** analytics engineering framework. The primary goal of dbt within our data platform is to manage ELT (Extract, Load, Transform) transformations directly inside cloud data warehouses (PostgreSQL, Snowflake, BigQuery, Databricks) by leveraging modern software engineering practices: modularity, version control, automated testing, documentation, and continuous integration.

```
       +-------------------------------------------------------------------------+
       |                        ELT Pipeline Architecture                        |
       +-------------------------------------------------------------------------+
       |                                                                         |
[Sources]  (Raw Ingestion: Fivetran / Airbyte / Kafka / Debezium)                |
   |                                                                             |
   v                                                                             |
+-------------------------------------------------------------------------------+|
| Database: raw schema                                                          ||
|   - raw_customers                                                             ||
|   - raw_orders                                                                ||
|   - raw_order_items                                                           ||
|   - raw_products                                                              ||
|   - raw_events                                                                ||
+-------------------------------------------------------------------------------+|
   |                                                                             |
   | dbt Execution Boundary (Transform Layer)                                    |
   v                                                                             |
+-------------------------------------------------------------------------------+|
| 1. STAGING LAYER (Schema: staging, Materialization: view)                     ||
|    stg_customers.sql, stg_orders.sql, stg_products.sql, stg_events.sql        ||
|    - Standardize column names (snake_case) & data types                       ||
|    - Primary key identification & string cleansing                             ||
+-------------------------------------------------------------------------------+|
   |                                                                             |
   v                                                                             |
+-------------------------------------------------------------------------------+|
| 2. INTERMEDIATE LAYER (Schema: intermediate, Materialization: view/ephemeral) ||
|    int_customer_orders.sql, int_order_items.sql                               ||
|    - Complex joins & calculations                                              ||
|    - Customer purchase history aggregation & order item pricing metrics        ||
+-------------------------------------------------------------------------------+|
   |                                                                             |
   v                                                                             |
+-------------------------------------------------------------------------------+|
| 3. MARTS LAYER (Schema: analytics_marts, Materialization: table/incremental)   ||
|    dim_customers.sql, dim_products.sql, fct_orders.sql                        ||
|    - Star-schema dimensional modeling                                         ||
|    - Surrogate keys via dbt_utils / md5                                       ||
|    - Incremental append/merge strategies                                      ||
+-------------------------------------------------------------------------------+|
   |                                                                             |
   v                                                                             |
+-------------------------------------------------------------------------------+|
| 4. ANALYTICS / REPORTING LAYER (Schema: analytics_marts)                      ||
|    rpt_sales_summary.sql, rpt_customer_cohorts.sql                            ||
|    - Executive BI aggregations                                                ||
|    - Cohort retention matrices & monthly performance metrics                  ||
+-------------------------------------------------------------------------------+|
   |                                                                             |
   v                                                                             |
[Downstream Consumers]                                                           |
   - BI Dashboards (Metabase, Tableau, Looker)                                  |
   - Operational Analytics (Reverse ETL to Salesforce/HubSpot)                 |
   - Machine Learning Feature Stores                                            |
```

---

## Modular Layering Design Strategy

### 1. Raw Layer (`raw` schema)
- **Role**: Landing zone for external extract/load tools.
- **Rules**: Immutable, unparsed, untransformed. Contains source system fields as ingested.
- **Access**: Strictly restricted to ingestion service accounts and dbt runner roles.

### 2. Staging Layer (`staging` schema / `models/staging/`)
- **Purpose**: Abstract raw data structures and enforce structural standardization.
- **Materialization**: `view` (Zero warehouse storage overhead; ensures fresh raw data evaluation).
- **Core Operations**:
  - Rename column headers to standardized `snake_case`.
  - Enforce explicit datatypes (e.g., `CAST(created_at AS TIMESTAMP)`).
  - Clean bad strings (`TRIM(LOWER(email))`).
  - Compute basic surrogate keys where natural keys are composite or missing.
- **Rule**: Staging models select ONLY from `source()` calls. No `ref()` joins across staging models.

### 3. Intermediate Layer (`intermediate` schema / `models/intermediate/`)
- **Purpose**: Execute complex business logic, structural joins, and multi-step aggregations before dimensional modeling.
- **Materialization**: `view` or `ephemeral` (CTE injection).
- **Core Operations**:
  - Join staging tables (e.g., combining order line items with product catalog prices).
  - Calculate derived financial metrics (gross margin, net revenue, discount distribution).
  - Aggregate temporal activity (customer first order date, total order count).
- **Rule**: Intermediate models are modular building blocks; never directly exposed to BI tools.

### 4. Marts Layer (`analytics` / `marts` schema / `models/marts/`)
- **Purpose**: Expose production dimensional models (Kimball Star-Schema) optimized for query performance and intuitive BI modeling.
- **Materialization**: `table` or `incremental` (Merge strategy).
- **Taxonomy**:
  - `dim_<entity>`: Dimension tables representing business entities (`dim_customers`, `dim_products`).
  - `fct_<event>`: Fact tables representing transactional metrics (`fct_orders`).
  - `rpt_<domain>`: Highly aggregated reporting datasets (`rpt_sales_summary`, `rpt_customer_cohorts`).

---

## Data Lineage & DAG Management

dbt parses SQL files containing `{{ ref('model_name') }}` and `{{ source('source_name', 'table_name') }}` Jinja functions to dynamically reconstruct a Directed Acyclic Graph (DAG).

```
                      +-------------------+
                      |   source('raw',   |
                      |   'customers')    |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      |   stg_customers   |
                      +---------+---------+
                                |
        +-----------------------+-----------------------+
        |                                               |
        v                                               v
+---------------+---------------+             +-------------------+
|  int_customer_orders          |             | customers_snapshot|
+---------------+---------------+             +-------------------+
        |                                               
        v                                               
+---------------+---------------+             +-------------------+
|   fct_orders  |-------------> |             |   dim_customers   |
+---------------+---------------+             +---------+---------+
        |                                               |
        +-----------------------+-----------------------+
                                |
                                v
                      +-------------------+
                      | rpt_sales_summary |
                      +-------------------+
```

### DAG Compilation Engine
1. **Parsing Phase**: Scans all SQL, YML, CSV files; extracts Jinja macros and dependency references.
2. **Compilation Phase**: Renders SQL files by substituting `ref()` and `source()` macros with physical schema/table names (`analytics_marts.fct_orders`).
3. **Execution Phase**: Computes topological sorting order and executes queries concurrently across configurable database connection threads (`threads: 4`).

---

## Materialization Mechanics

| Materialization | Underlying DDL / DML Generated | Primary Use Case | Performance Implications |
|-----------------|--------------------------------|------------------|--------------------------|
| **View** | `CREATE VIEW target AS SELECT ...` | Staging & Intermediate models | Fast build time; query compute cost deferred to read time |
| **Table** | `CREATE TABLE target AS SELECT ...` | Small/Medium Dimensions & Marts | Longer build time; optimal BI read performance |
| **Incremental** | `CREATE TEMP TABLE ...; MERGE INTO target USING temp ...` | Large Fact tables (`fct_orders`) | Fast periodic updates; minimal warehouse compute during dbt runs |
| **Ephemeral** | CTE injection (`WITH model AS (...) SELECT ...`) | Helper queries, single-use transformations | Zero database object overhead; cleanly isolates Jinja modularity |

---

## Snapshot & Change Data Capture Architecture (SCD Type 2)

dbt Snapshots record historical attribute mutations over time (Type 2 Slowly Changing Dimensions).

- **Strategy**: `timestamp` (uses `updated_at` column) or `check` (hashes specified columns).
- **Mechanism**: Maintains `dbt_updated_at`, `dbt_valid_from`, and `dbt_valid_to` metadata fields.
- **Workflow**:
  1. Identifies existing records in target snapshot schema.
  2. Compares record states using specified `updated_at` or `check_cols` hash.
  3. Closes updated record by populating `dbt_valid_to = current_timestamp`.
  4. Inserts new record version with `dbt_valid_from = current_timestamp` and `dbt_valid_to = NULL`.

---

## State Management & Artifacts

dbt produces JSON artifacts in the `target/` directory during execution:
- `manifest.json`: Full structural representation of the project DAG, node properties, and documentation.
- `run_results.json`: Detailed execution metadata (status, execution timing, rows affected, query IDs, adapter responses).
- `catalog.json`: Data warehouse metadata extracted during `dbt docs generate` (column types, table sizes, row counts).

### Slim CI State Comparison
By persisting `manifest.json` from production runs, CI pipelines execute targeted runs using:
```bash
dbt run --select state:modified+ --state path/to/prod/artifacts
```
This isolates testing strictly to modified files and their downstream dependencies, reducing execution costs by up to 90%.
