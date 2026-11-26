-- Project 02: Enterprise Data Warehouse DDL Schema (SQLite / PostgreSQL Compatible)

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS fact_payments;
DROP TABLE IF EXISTS fact_invoices;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_inventory;
DROP TABLE IF EXISTS healthcare_claims;
DROP TABLE IF EXISTS banking_transactions;
DROP TABLE IF EXISTS iot_sensor_data;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_employees;
DROP TABLE IF EXISTS dim_departments;
DROP TABLE IF EXISTS stg_sales_incremental;

-- Dimension Tables
CREATE TABLE dim_customers (
    customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    effective_start_date TEXT NOT NULL,
    effective_end_date TEXT,
    is_current INTEGER DEFAULT 1
);

CREATE TABLE dim_departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL,
    manager_name TEXT,
    location TEXT
);

CREATE TABLE dim_employees (
    employee_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    department_id INTEGER,
    salary REAL NOT NULL,
    manager_id INTEGER,
    hire_date TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES dim_departments(department_id)
);

CREATE TABLE dim_products (
    product_key INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    unit_price REAL NOT NULL,
    cost_price REAL NOT NULL
);

-- Fact Tables
CREATE TABLE fact_sales (
    sales_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL UNIQUE,
    customer_key INTEGER NOT NULL,
    product_key INTEGER NOT NULL,
    sale_date TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    gross_amount REAL NOT NULL,
    discount_amount REAL DEFAULT 0.0,
    net_amount REAL NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (customer_key) REFERENCES dim_customers(customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_products(product_key)
);

CREATE TABLE fact_orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    customer_key INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    order_status TEXT NOT NULL,
    total_amount REAL NOT NULL,
    FOREIGN KEY (customer_key) REFERENCES dim_customers(customer_key)
);

CREATE TABLE fact_payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_reference TEXT NOT NULL UNIQUE,
    order_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    payment_amount REAL NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES fact_orders(order_id)
);

CREATE TABLE fact_invoices (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT NOT NULL UNIQUE,
    customer_key INTEGER NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    invoice_amount REAL NOT NULL,
    paid_amount REAL DEFAULT 0.0,
    status TEXT NOT NULL
);

CREATE TABLE fact_transactions (
    txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    txn_timestamp TEXT NOT NULL,
    txn_type TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD'
);

CREATE TABLE fact_inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_key INTEGER NOT NULL,
    warehouse_location TEXT NOT NULL,
    stock_quantity INTEGER NOT NULL,
    reorder_level INTEGER NOT NULL,
    last_updated TEXT NOT NULL,
    FOREIGN KEY (product_key) REFERENCES dim_products(product_key)
);

CREATE TABLE healthcare_claims (
    claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    diagnosis_code TEXT NOT NULL,
    claim_amount REAL NOT NULL,
    approved_amount REAL NOT NULL,
    claim_date TEXT NOT NULL,
    claim_status TEXT NOT NULL
);

CREATE TABLE banking_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    transaction_date TEXT NOT NULL
);

CREATE TABLE iot_sensor_data (
    reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    reading_value REAL NOT NULL,
    reading_time TEXT NOT NULL
);

CREATE TABLE audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE stg_sales_incremental (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    sale_date TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL
);
