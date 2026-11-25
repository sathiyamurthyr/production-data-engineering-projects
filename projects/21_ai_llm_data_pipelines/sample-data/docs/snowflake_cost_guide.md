# Snowflake Cost & Warehouse Governance Guide

## Virtual Warehouse Sizing
Separate ETL ingestion warehouses from BI reporting warehouses. Enable `AUTO_SUSPEND = 60` seconds and `AUTO_RESUME = TRUE` to eliminate idle compute billing.

## Micro-Partition Pruning & Clustering
Snowflake stores tables in 16 MB compressed micro-partitions. Define clustering keys only on multi-terabyte tables filtered frequently by date or tenant_id.

## Streams & Dynamic Tables
Use Snowflake Streams with Tasks or Dynamic Tables (`TARGET_LAG = '5 minutes'`) for declarative incremental pipelines instead of full-table overwrites.
