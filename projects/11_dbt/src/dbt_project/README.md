# Production dbt Project

This directory contains the complete **dbt Core project** for retail analytics data engineering.

## Quick CLI Reference

```bash
# Install dependencies
dbt deps

# Seed reference data
dbt seed

# Run snapshots
dbt snapshot

# Run all models
dbt run

# Run tests
dbt test

# Generate interactive DAG docs
dbt docs generate && dbt docs serve --port 8080
```

## Structure Overview

- `models/staging`: Raw table cleanups and standardizations (views)
- `models/intermediate`: Multi-table joins and intermediate metrics (views/ephemeral)
- `models/marts/sales`: Star-schema facts and dimensions (`fct_orders`, `dim_customers`, `dim_products`)
- `models/marts/analytics`: BI-ready rollups (`rpt_sales_summary`, `rpt_customer_cohorts`)
- `macros`: Reusable Jinja macros (`generate_surrogate_key`, `pivot_values`, `audit_helper`, `date_spine`)
- `seeds`: Reference CSV datasets (`country_codes.csv`, `product_categories.csv`)
- `snapshots`: SCD Type 2 tracking (`customers_snapshot.sql`)
