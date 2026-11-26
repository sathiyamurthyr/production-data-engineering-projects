# Design Decisions & Warehouse Schema Modelling

This document details the architectural decisions and database modeling choices implemented in this Amazon Redshift project.

---

## 1. Schema Isolation: Staging vs. Core
To prevent data contamination and ensure consistent transactional integrity:
- **`staging` Schema:** Serves as a volatile landing zone. Tables are modeled with minimal constraints and flexible datatypes to prevent ingestion pipeline crashes. Rows are ingested using S3 `COPY` commands and truncated immediately post-load to keep the disk footprint low.
- **`core` Schema:** Implements a clean, optimized star-schema structure. Contains enterprise fact and dimension tables. Every table is defined with optimal column compression, strict distribution styles, and sort keys.

---

## 2. Distribution Key Modeling Decisions
Data movement across the internal cluster network is the most expensive operation in an MPP architecture. We implemented the following distribution styles to minimize network traffic:

| Table Name | Distribution Style | Key Column | Rationale |
| :--- | :--- | :--- | :--- |
| `core.fact_sales` | **KEY** | `customer_id` | Fact table joined extensively with customer details. |
| `core.dim_customer` | **KEY** | `customer_id` | Joined on the same key as the fact table, enabling **Colocated Joins** (eliminating network reshuffling, producing `DS_DIST_NONE`). |
| `core.dim_payment_method` | **ALL** | *None* | A small lookup table (< 1,000 rows). Copying it to every node prevents network transit during joins. |

---

## 3. Sort Key Selection Strategy
Sort keys determine the physical sorting order of data within each 1MB block on disk, enabling effective pruning via Zone Maps:
- **`core.fact_sales` (Compound Sort Key: `sale_date`, `product_id`):** 
  - *Why Compound?* High-frequency analytics queries filter on chronological ranges (e.g. "past 30 days") first, followed by product aggregations.
  - *Why `sale_date` first?* In compound sort keys, the hierarchical structure makes the primary key critical. Filtering on `product_id` alone yields limited zone map gains.
- **Interleaved Sort Key Comparison:** Evaluated on `sales_interleaved_sort` (`customer_id`, `product_id`) for ad-hoc analytical queries where users filter by product or customer dynamically. It was decided to limit interleaved keys because the vacuum and reindex costs on write workloads are 5x higher than compound keys.

---

## 4. Column Compression Encoding Configuration
Redshift stores data in a columnar fashion. We applied explicit encodings to save up to 80% storage and improve scan I/O:
- **`AZ64` Encoding:** Applied to all numeric (`INT`, `BIGINT`, `NUMERIC`) and date/time columns. It yields higher compression ratios and faster scan performance than ZSTD or LZO.
- **`ZSTD` Encoding:** Applied to large variable string columns (`VARCHAR(50)+`) due to its excellent dictionary compression ratio.
- **`RAW` Encoding:** Configured on the leading column of the sort key (`sale_date` in `fact_sales`). Keeping the leading sort key column uncompressed prevents the compute node from wasting CPU cycles decompressing index headers during block skipping.

---

## 5. Mock Mode Integration for Local Testing
To ensure the repository is testable locally without provisioning an expensive AWS Redshift cluster:
- **Dynamic Connection Fallback:** If `psycopg2` is missing or connectivity times out (e.g., in a CI/CD environment), the application switches to `MockRedshiftConnection`.
- **System Table Simulation:** The mock cursor mimics system views like `svv_table_info`, `svv_mv_info`, and `stv_locks` so metadata tools, unit tests, and utility functions run successfully in any environment.
