"""
DAG: 03_sql_dag.py
==================

PURPOSE:
    Demonstrates database-centric DAG patterns using SQLExecuteQueryOperator,
    SQLCheckOperator, SQLValueCheckOperator, and SQLThresholdCheckOperator.
    Shows how to orchestrate multi-step SQL workflows with dependency management.

CONCEPTS COVERED:
    1. SQLExecuteQueryOperator — execute DDL/DML SQL against any DB connection
    2. SQLCheckOperator — assert a SQL query returns at least one non-zero/non-null row
    3. SQLValueCheckOperator — assert a specific column equals an expected value
    4. SQLThresholdCheckOperator — assert a metric is within a min/max range
    5. Connection management — using Airflow Connections (conn_id) securely
    6. SQL templating — using Jinja in SQL strings for dynamic queries
    7. Multi-step SQL workflow — create staging → insert → validate → promote

BUSINESS USE CASE:
    Daily finance reconciliation pipeline:
    1. Create staging table for today's GL entries
    2. Load GL data from source system (ERP → Data Warehouse)
    3. Validate totals match expected values from source
    4. Ensure row counts are within historical thresholds
    5. Promote validated data to production tables
    6. Generate daily financial summary view

SQL WORKFLOW:
    create_staging → load_gl_entries → check_row_count → check_total_balance
        → check_debit_credit_equality → promote_to_production → refresh_summary_view

SECURITY NOTES:
    - NEVER hardcode credentials in DAG files — use Airflow Connections
    - Connection strings are encrypted in the Metadata DB (Fernet key)
    - Use PostgresHook / SnowflakeHook for advanced connection patterns
    - SQL files should be stored in a separate /sql directory, not inline strings
      for large queries (improves testability and diffs)

PERFORMANCE NOTES:
    - SQLExecuteQueryOperator opens a new DB connection per task
    - For bulk loads, use COPY / BULK INSERT instead of row-by-row INSERT
    - Set conn_pool_size in airflow.cfg for connection pooling
    - Use SET statement_timeout on long-running PostgreSQL queries

INTERVIEW QUESTIONS:
    Q: How do Airflow Connections work?
    A: Connections store credentials (host, port, login, password, schema) encrypted
       in the metadata DB. Reference them by conn_id. Never hardcode credentials.
       Connections can also be stored as environment variables:
       AIRFLOW_CONN_MY_PG=postgresql://user:pass@host:5432/dbname

    Q: What is the difference between SQLCheckOperator and SQLValueCheckOperator?
    A: SQLCheckOperator: ensures query returns non-zero/non-null values (pass/fail)
       SQLValueCheckOperator: ensures a specific value equals an expected number
       SQLThresholdCheckOperator: ensures a metric is within min/max bounds

    Q: How do you pass dynamic SQL parameters safely (avoiding SQL injection)?
    A: Use Jinja templating for execution_date and context variables.
       For user-provided values, use parameterized queries via the hook directly.
       Never format user input directly into SQL strings.

    Q: Can you run multiple SQL statements in one SQLExecuteQueryOperator?
    A: Yes, pass a list of SQL strings or a multi-statement string. Behavior
       depends on the database and autocommit settings.

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.common.sql.operators.sql import (
    SQLCheckOperator,
    SQLExecuteQueryOperator,
    SQLThresholdCheckOperator,
    SQLValueCheckOperator,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONNECTION ID
# Set this connection in Airflow UI: Admin → Connections
# Type: Postgres | Host: localhost | Schema: finance_db | Login: airflow | Port: 5432
# ---------------------------------------------------------------------------
CONN_ID = "postgres_finance_db"

# ---------------------------------------------------------------------------
# DEFAULT ARGS
# ---------------------------------------------------------------------------
default_args: dict = {
    "owner": "data-engineering-diaries",
    "email_on_failure": True,
    "email": ["finance-data-team@company.com"],
    "retries": 2,
    "retry_delay": timedelta(minutes=15),
    "execution_timeout": timedelta(hours=3),
}

# ---------------------------------------------------------------------------
# SQL DEFINITIONS
# In production, these would be loaded from .sql files using:
#   sql="{% include 'sql/create_staging_gl.sql' %}"
# or stored in a sql/ subdirectory and passed as file path.
# ---------------------------------------------------------------------------

SQL_CREATE_STAGING = """
-- Create or replace the daily staging table for GL entries
-- Partitioned by execution date for efficient querying
CREATE TABLE IF NOT EXISTS staging.gl_entries_{{ ds_nodash }} (
    entry_id        BIGSERIAL PRIMARY KEY,
    ledger_date     DATE          NOT NULL,
    account_code    VARCHAR(20)   NOT NULL,
    account_name    VARCHAR(200)  NOT NULL,
    debit_amount    NUMERIC(18,4) NOT NULL DEFAULT 0,
    credit_amount   NUMERIC(18,4) NOT NULL DEFAULT 0,
    currency_code   CHAR(3)       NOT NULL DEFAULT 'USD',
    cost_center     VARCHAR(50),
    journal_ref     VARCHAR(100)  NOT NULL,
    source_system   VARCHAR(50)   NOT NULL DEFAULT 'ERP',
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_amounts CHECK (debit_amount >= 0 AND credit_amount >= 0),
    CONSTRAINT chk_not_both_zero CHECK (debit_amount > 0 OR credit_amount > 0)
);

-- Create index on account_code for fast lookups
CREATE INDEX IF NOT EXISTS idx_gl_{{ ds_nodash }}_account
    ON staging.gl_entries_{{ ds_nodash }} (account_code);

-- Truncate if it already has data from a previous run (idempotency)
TRUNCATE TABLE staging.gl_entries_{{ ds_nodash }};
"""

SQL_LOAD_GL_ENTRIES = """
-- Load GL entries from source ERP system into staging
-- Using INSERT ... SELECT from a federated source or pre-staged raw table
-- Template variable {{ ds }} resolves to execution date 'YYYY-MM-DD'
INSERT INTO staging.gl_entries_{{ ds_nodash }} (
    ledger_date, account_code, account_name,
    debit_amount, credit_amount, currency_code,
    cost_center, journal_ref, source_system
)
SELECT
    entry_date::DATE            AS ledger_date,
    account_code,
    account_name,
    COALESCE(debit_amount,  0)  AS debit_amount,
    COALESCE(credit_amount, 0)  AS credit_amount,
    COALESCE(currency_code, 'USD') AS currency_code,
    cost_center,
    journal_reference           AS journal_ref,
    'ERP'                       AS source_system
FROM raw.erp_gl_entries
WHERE entry_date = '{{ ds }}'::DATE
  AND is_posted = TRUE
  AND is_reversed = FALSE
ON CONFLICT (entry_id) DO NOTHING;  -- Idempotent re-runs
"""

SQL_CHECK_ROW_COUNT = """
-- SQLCheckOperator: returns True if count > 0
-- Fails the task if no rows were loaded (upstream data issue)
SELECT COUNT(*)
FROM staging.gl_entries_{{ ds_nodash }}
WHERE ledger_date = '{{ ds }}'::DATE
"""

SQL_CHECK_DEBIT_CREDIT_BALANCE = """
-- SQLValueCheckOperator: debits must equal credits in a balanced ledger
-- Returns the absolute difference — expect 0.0000
SELECT ABS(
    SUM(debit_amount) - SUM(credit_amount)
)::NUMERIC(18,4)
FROM staging.gl_entries_{{ ds_nodash }}
WHERE ledger_date = '{{ ds }}'::DATE
"""

SQL_CHECK_TOTAL_THRESHOLD = """
-- SQLThresholdCheckOperator: total transaction value must be within bounds
-- Returns the total daily transaction volume
SELECT SUM(debit_amount + credit_amount)
FROM staging.gl_entries_{{ ds_nodash }}
WHERE ledger_date = '{{ ds }}'::DATE
"""

SQL_PROMOTE_TO_PRODUCTION = """
-- Promote validated staging data to the production table
-- Using MERGE / INSERT ... ON CONFLICT for idempotency
INSERT INTO production.gl_entries (
    ledger_date, account_code, account_name,
    debit_amount, credit_amount, currency_code,
    cost_center, journal_ref, source_system, loaded_at
)
SELECT
    ledger_date, account_code, account_name,
    debit_amount, credit_amount, currency_code,
    cost_center, journal_ref, source_system,
    NOW() AS loaded_at
FROM staging.gl_entries_{{ ds_nodash }}
WHERE ledger_date = '{{ ds }}'::DATE
ON CONFLICT (ledger_date, journal_ref, account_code)
DO UPDATE SET
    debit_amount  = EXCLUDED.debit_amount,
    credit_amount = EXCLUDED.credit_amount,
    loaded_at     = NOW();
"""

SQL_REFRESH_SUMMARY = """
-- Refresh the daily financial summary materialized view
-- This updates the BI dashboard cache
REFRESH MATERIALIZED VIEW CONCURRENTLY production.daily_financial_summary;

-- Update pipeline metadata
INSERT INTO audit.pipeline_runs (dag_id, execution_date, status, row_count, run_at)
VALUES (
    'finance_gl_reconciliation',
    '{{ ds }}'::DATE,
    'SUCCESS',
    (SELECT COUNT(*) FROM staging.gl_entries_{{ ds_nodash }}),
    NOW()
)
ON CONFLICT (dag_id, execution_date) DO UPDATE SET
    status   = 'SUCCESS',
    row_count = EXCLUDED.row_count,
    run_at    = NOW();
"""

SQL_CLEANUP_OLD_STAGING = """
-- Cleanup staging tables older than 7 days to manage storage
-- Run in a separate task to not block the main pipeline
DO $$
DECLARE
    tbl_name TEXT;
    cutoff_date DATE := CURRENT_DATE - INTERVAL '7 days';
BEGIN
    FOR tbl_name IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'staging'
          AND tablename LIKE 'gl_entries_%'
          AND TO_DATE(SUBSTRING(tablename FROM 'gl_entries_(.+)'), 'YYYYMMDD') < cutoff_date
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS staging.' || tbl_name;
        RAISE NOTICE 'Dropped staging table: %', tbl_name;
    END LOOP;
END $$;
"""

# ---------------------------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------------------------
with DAG(
    dag_id="03_sql_finance_reconciliation",
    description="SQL-centric DAG: GL reconciliation with validation and data quality checks",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 7 * * 1-5",    # Weekdays (Mon–Fri) at 07:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=["sql", "finance", "reconciliation", "data-quality", "data-engineering-diaries"],
    doc_md="""
## Finance GL Reconciliation DAG

Orchestrates the daily General Ledger reconciliation process:

1. **Create staging table** — partitioned daily staging table
2. **Load GL entries** — insert from ERP raw layer
3. **Row count check** — ensure data was loaded
4. **Balance check** — debits must equal credits
5. **Threshold check** — total volume within historical bounds
6. **Promote to production** — UPSERT into production table
7. **Refresh summary view** — update BI dashboards
8. **Cleanup staging** — drop 7-day-old staging tables

### Connection Required
Set `postgres_finance_db` in Admin → Connections.

### Schedule: Mon–Fri 07:00 UTC
    """,
) as dag:

    start = EmptyOperator(task_id="start")

    # -----------------------------------------------------------------------
    # TASK 1: Create daily staging table (DDL)
    # -----------------------------------------------------------------------
    create_staging = SQLExecuteQueryOperator(
        task_id="create_staging_table",
        conn_id=CONN_ID,
        sql=SQL_CREATE_STAGING,
        autocommit=True,
        doc_md="Create and truncate the daily GL staging table.",
    )

    # -----------------------------------------------------------------------
    # TASK 2: Load GL entries from raw ERP source
    # -----------------------------------------------------------------------
    load_gl = SQLExecuteQueryOperator(
        task_id="load_gl_entries",
        conn_id=CONN_ID,
        sql=SQL_LOAD_GL_ENTRIES,
        autocommit=True,
        doc_md="INSERT GL entries from raw.erp_gl_entries into staging table.",
    )

    # -----------------------------------------------------------------------
    # TASK 3: Check that rows were actually loaded (non-zero count)
    # SQLCheckOperator: PASSES if the query returns a non-zero/non-null value
    # FAILS if query returns 0, NULL, empty, or False
    # -----------------------------------------------------------------------
    check_rows_loaded = SQLCheckOperator(
        task_id="check_rows_loaded",
        conn_id=CONN_ID,
        sql=SQL_CHECK_ROW_COUNT,
        doc_md="Assert that at least one GL entry was loaded for the execution date.",
    )

    # -----------------------------------------------------------------------
    # TASK 4: Validate debit/credit balance equality
    # SQLValueCheckOperator: PASSES if query result equals pass_value
    # -----------------------------------------------------------------------
    check_balance = SQLValueCheckOperator(
        task_id="check_debit_credit_balance",
        conn_id=CONN_ID,
        sql=SQL_CHECK_DEBIT_CREDIT_BALANCE,
        pass_value=0.0,     # Difference must be exactly 0 (balanced ledger)
        tolerance=0.0001,   # Allow 0.01% tolerance for floating-point rounding
        doc_md="Assert that total debits equal total credits (balanced ledger principle).",
    )

    # -----------------------------------------------------------------------
    # TASK 5: Check total transaction volume is within historical bounds
    # SQLThresholdCheckOperator: PASSES if min_threshold <= result <= max_threshold
    # -----------------------------------------------------------------------
    check_volume = SQLThresholdCheckOperator(
        task_id="check_transaction_volume",
        conn_id=CONN_ID,
        sql=SQL_CHECK_TOTAL_THRESHOLD,
        min_threshold=10_000.00,      # At least $10K daily (avoids ghost runs)
        max_threshold=1_000_000_000,  # At most $1B daily (anomaly detection)
        doc_md="Assert daily GL transaction volume is within expected bounds.",
    )

    # -----------------------------------------------------------------------
    # TASK 6: Promote validated staging data to production
    # -----------------------------------------------------------------------
    promote_to_prod = SQLExecuteQueryOperator(
        task_id="promote_to_production",
        conn_id=CONN_ID,
        sql=SQL_PROMOTE_TO_PRODUCTION,
        autocommit=True,
        doc_md="UPSERT validated GL entries into production.gl_entries.",
    )

    # -----------------------------------------------------------------------
    # TASK 7: Refresh materialized view for BI dashboards
    # -----------------------------------------------------------------------
    refresh_summary = SQLExecuteQueryOperator(
        task_id="refresh_summary_view",
        conn_id=CONN_ID,
        sql=SQL_REFRESH_SUMMARY,
        autocommit=True,
        doc_md="Refresh production.daily_financial_summary materialized view.",
    )

    # -----------------------------------------------------------------------
    # TASK 8: Cleanup old staging tables (runs in parallel with refresh)
    # -----------------------------------------------------------------------
    cleanup_staging = SQLExecuteQueryOperator(
        task_id="cleanup_old_staging",
        conn_id=CONN_ID,
        sql=SQL_CLEANUP_OLD_STAGING,
        autocommit=True,
        doc_md="Drop staging tables older than 7 days to free disk space.",
    )

    end = EmptyOperator(task_id="end")

    # -----------------------------------------------------------------------
    # TASK DEPENDENCIES
    # -----------------------------------------------------------------------
    (
        start
        >> create_staging
        >> load_gl
        >> check_rows_loaded
        >> check_balance
        >> check_volume
        >> promote_to_prod
        >> [refresh_summary, cleanup_staging]
        >> end
    )
