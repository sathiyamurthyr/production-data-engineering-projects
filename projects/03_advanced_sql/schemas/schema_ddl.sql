-- =============================================================================
-- Schema DDL for 03 Advanced SQL for Data Engineering
-- =============================================================================
-- File        : schema_ddl.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : SQLite / PostgreSQL / ANSI SQL
-- =============================================================================

-- Module 01: Employees Hierarchy
CREATE TABLE IF NOT EXISTS employees (
    employee_id   INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    job_title     TEXT NOT NULL,
    department    TEXT NOT NULL,
    manager_id    INTEGER REFERENCES employees(employee_id),
    salary        REAL NOT NULL,
    hire_date     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(manager_id);

-- Module 02: Sales & Budget
CREATE TABLE IF NOT EXISTS monthly_sales (
    sale_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    product     TEXT NOT NULL,
    region      TEXT NOT NULL,
    sale_month  INTEGER NOT NULL,
    sale_year   INTEGER NOT NULL,
    revenue     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS quarterly_budget (
    department  TEXT PRIMARY KEY,
    q1_budget   REAL,
    q2_budget   REAL,
    q3_budget   REAL,
    q4_budget   REAL
);

-- Module 03: API Events JSON
CREATE TABLE IF NOT EXISTS api_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    source      TEXT NOT NULL,
    received_at TEXT NOT NULL,
    payload     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders_clean (
    order_id        TEXT PRIMARY KEY,
    customer_id     INTEGER,
    customer_name   TEXT,
    customer_email  TEXT,
    customer_tier   TEXT,
    order_total     REAL,
    currency        TEXT,
    shipping_method TEXT,
    shipping_days   INTEGER,
    campaign_id     TEXT,
    referrer        TEXT,
    tags            TEXT,
    source          TEXT,
    received_at     TEXT
);

-- Module 04: Customers & Orders
CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    country       TEXT NOT NULL,
    signup_date   TEXT NOT NULL,
    segment       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date    TEXT NOT NULL,
    product_name  TEXT NOT NULL,
    amount        REAL NOT NULL,
    status        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_date ON orders(customer_id, order_date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_customer_amount ON orders(customer_id, amount DESC);

CREATE TABLE IF NOT EXISTS product_tags (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    tags_csv     TEXT NOT NULL
);

-- Module 05: Daily Metrics
CREATE TABLE IF NOT EXISTS daily_metrics (
    metric_id     INTEGER PRIMARY KEY,
    metric_date   TEXT NOT NULL,
    store_id      INTEGER NOT NULL,
    daily_revenue REAL NOT NULL,
    transaction_cnt INTEGER NOT NULL
);

-- Module 06: Ledger Transactions
CREATE TABLE IF NOT EXISTS ledger_transactions (
    txn_id        INTEGER PRIMARY KEY,
    account_id    INTEGER NOT NULL,
    txn_date      TEXT NOT NULL,
    txn_amount    REAL NOT NULL,
    txn_type      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_acct_date ON ledger_transactions(account_id, txn_date, txn_id);

-- Module 07: User Logins & Invoices & Server Status
CREATE TABLE IF NOT EXISTS user_logins (
    login_id    INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    login_date  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_sequence (
    seq_id    INTEGER PRIMARY KEY,
    status    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS server_status (
    event_time TEXT PRIMARY KEY,
    server_id  INTEGER NOT NULL,
    status     TEXT NOT NULL
);

-- Module 08: Product Daily Sales
CREATE TABLE IF NOT EXISTS product_daily_sales (
    sale_date    TEXT NOT NULL,
    product_id   INTEGER NOT NULL,
    units_sold   INTEGER NOT NULL,
    unit_price   REAL NOT NULL,
    PRIMARY KEY (sale_date, product_id)
);

-- Module 09: Target & Staging Customers
CREATE TABLE IF NOT EXISTS target_customers (
    customer_id   INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL,
    tier          TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging_customers (
    customer_id   INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL,
    tier          TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- Module 10: Regional Sales
CREATE TABLE IF NOT EXISTS regional_sales (
    sales_id    INTEGER PRIMARY KEY,
    year        INTEGER NOT NULL,
    region      TEXT NOT NULL,
    category    TEXT NOT NULL,
    amount      REAL NOT NULL
);

-- Module 11: SCD Type 2
CREATE TABLE IF NOT EXISTS dim_employee_scd2 (
    employee_sk   INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    department    TEXT NOT NULL,
    salary        REAL NOT NULL,
    valid_from    TEXT NOT NULL,
    valid_to      TEXT NOT NULL,
    is_current    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging_employee_updates (
    employee_id   INTEGER PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department    TEXT NOT NULL,
    salary        REAL NOT NULL,
    effective_ts  TEXT NOT NULL
);

-- Module 12: Data Vault 2.0
CREATE TABLE IF NOT EXISTS hub_customer (
    hk_customer_id TEXT PRIMARY KEY,
    customer_id    INTEGER NOT NULL,
    load_date      TEXT NOT NULL,
    record_source  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hub_store (
    hk_store_id   TEXT PRIMARY KEY,
    store_id      INTEGER NOT NULL,
    load_date     TEXT NOT NULL,
    record_source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS link_customer_store (
    hk_link_cust_store TEXT PRIMARY KEY,
    hk_customer_id     TEXT NOT NULL REFERENCES hub_customer(hk_customer_id),
    hk_store_id        TEXT NOT NULL REFERENCES hub_store(hk_store_id),
    load_date          TEXT NOT NULL,
    record_source      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sat_customer_profile (
    hk_customer_id TEXT NOT NULL REFERENCES hub_customer(hk_customer_id),
    load_date      TEXT NOT NULL,
    customer_name  TEXT NOT NULL,
    email          TEXT NOT NULL,
    address        TEXT NOT NULL,
    hash_diff      TEXT NOT NULL,
    record_source  TEXT NOT NULL,
    PRIMARY KEY (hk_customer_id, load_date)
);

-- Module 13: Web Logs
CREATE TABLE IF NOT EXISTS web_logs (
    log_id       INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL,
    url_path     TEXT NOT NULL,
    status_code  INTEGER NOT NULL,
    response_ms  REAL NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_web_logs_user_status ON web_logs(user_id, status_code);
CREATE INDEX IF NOT EXISTS idx_web_logs_created_at ON web_logs(created_at);

-- Module 14: Partitioned Orders
CREATE TABLE IF NOT EXISTS partitioned_orders (
    order_id     INTEGER PRIMARY KEY,
    order_date   TEXT NOT NULL,
    country_code TEXT NOT NULL,
    total_amount REAL NOT NULL
);

-- Module 15: Orders Raw & Materialized View Summary
CREATE TABLE IF NOT EXISTS orders_raw (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    order_date   TEXT NOT NULL,
    amount       REAL NOT NULL,
    status       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mv_customer_sales_summary (
    customer_id        INTEGER PRIMARY KEY,
    total_orders       INTEGER NOT NULL,
    completed_revenue  REAL NOT NULL,
    last_order_date    TEXT NOT NULL,
    refreshed_at       TEXT NOT NULL
);

-- Module 16: Clickstream Events
CREATE TABLE IF NOT EXISTS clickstream_events (
    event_id    INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    event_time  TEXT NOT NULL,
    page_name   TEXT NOT NULL
);

-- Module 17: User Cohorts & Activity
CREATE TABLE IF NOT EXISTS user_cohort_signups (
    user_id     INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_monthly_activity (
    activity_id   INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    activity_date TEXT NOT NULL
);

-- Module 18: CDC Stream & Snapshot
CREATE TABLE IF NOT EXISTS cdc_orders_stream (
    cdc_id        INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL,
    customer_id   INTEGER NOT NULL,
    amount        REAL NOT NULL,
    status        TEXT NOT NULL,
    cdc_op        TEXT NOT NULL,
    lsn_seq       INTEGER NOT NULL,
    cdc_timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders_current_snapshot (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL,
    amount        REAL NOT NULL,
    status        TEXT NOT NULL,
    last_updated  TEXT NOT NULL
);

-- Module 19: Market Basket Items
CREATE TABLE IF NOT EXISTS order_basket_items (
    basket_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL,
    product_name TEXT NOT NULL
);

-- Module 20: ETL Audit Log & Production Pipeline Tables
CREATE TABLE IF NOT EXISTS etl_pipeline_audit_log (
    job_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name  TEXT NOT NULL,
    start_time     TEXT NOT NULL,
    end_time       TEXT,
    rows_processed INTEGER DEFAULT 0,
    status         TEXT NOT NULL,
    error_message  TEXT
);

CREATE TABLE IF NOT EXISTS stg_raw_transactions (
    raw_id         INTEGER PRIMARY KEY,
    txn_id         INTEGER NOT NULL,
    customer_id    INTEGER,
    amount         REAL,
    txn_timestamp  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prod_transactions (
    txn_id         INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL,
    amount         REAL NOT NULL,
    txn_timestamp  TEXT NOT NULL,
    loaded_at      TEXT NOT NULL
);
