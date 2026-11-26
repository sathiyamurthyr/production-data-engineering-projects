# Lakehouse Medallion Architecture Runbook

## Bronze Layer Ingestion
The Bronze layer stores raw, immutable source events from Kafka topics, REST APIs, and CDC streams in Parquet or Delta format. Every record includes `_ingested_at`, `_source_file`, and `_batch_id` metadata columns for full auditability.

## Silver Layer Cleansing & Deduplication
In the Silver layer, streaming and batch jobs deduplicate records using `ROW_NUMBER()` over primary keys ordered by LSN or event timestamp. Schema enforcement and PII redaction happen before data reaches downstream analysts.

## Gold Layer Business Marts
Gold tables expose star-schema dimensional models (`dim_customers`, `dim_products`, `fact_orders`) optimized with Z-Ordering or liquid clustering for BI dashboards and ML feature stores.
