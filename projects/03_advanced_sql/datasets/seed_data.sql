-- =============================================================================
-- Seed Data for 03 Advanced SQL for Data Engineering
-- =============================================================================
-- File        : seed_data.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : SQLite / PostgreSQL / ANSI SQL
-- =============================================================================

-- Module 01: Employees
INSERT INTO employees (employee_id, full_name, job_title, department, manager_id, salary, hire_date) VALUES
    (1,  'Alice Johnson',  'CEO',              'Executive',    NULL, 450000.00, '2015-01-10'),
    (2,  'Bob Smith',      'CTO',              'Technology',   1,    320000.00, '2015-03-15'),
    (3,  'Carol Davis',    'CFO',              'Finance',      1,    310000.00, '2015-03-15'),
    (4,  'Dave Wilson',    'COO',              'Operations',   1,    305000.00, '2016-06-01'),
    (5,  'Eve Martinez',   'Backend Lead',     'Technology',   2,    180000.00, '2017-09-01'),
    (6,  'Frank Lee',      'Data Lead',        'Technology',   2,    190000.00, '2018-02-14'),
    (7,  'Grace Patel',    'Finance Manager',  'Finance',      3,    140000.00, '2019-04-22'),
    (8,  'Henry Brown',    'Ops Manager',      'Operations',   4,    135000.00, '2019-07-08'),
    (9,  'Ivy Chen',       'Senior Engineer',  'Technology',   5,    140000.00, '2020-01-15'),
    (10, 'Jack Taylor',    'Data Engineer',    'Technology',   6,    125000.00, '2021-03-01'),
    (11, 'Kim Anderson',   'Data Analyst',     'Technology',   6,    105000.00, '2022-06-15'),
    (12, 'Leo Thomas',     'Ops Analyst',      'Operations',   8,     95000.00, '2023-01-10')
ON CONFLICT(employee_id) DO NOTHING;

-- Module 02: Monthly Sales & Quarterly Budget
INSERT INTO monthly_sales (sale_id, product, region, sale_month, sale_year, revenue) VALUES
    (1,  'Laptop',  'North', 1, 2024, 150000.00),
    (2,  'Laptop',  'North', 2, 2024,  95000.00),
    (3,  'Laptop',  'North', 3, 2024, 210000.00),
    (4,  'Laptop',  'South', 1, 2024,  80000.00),
    (5,  'Laptop',  'South', 2, 2024, 120000.00),
    (6,  'Laptop',  'South', 3, 2024, 140000.00),
    (7,  'Phone',   'North', 1, 2024, 200000.00),
    (8,  'Phone',   'North', 2, 2024, 175000.00),
    (9,  'Phone',   'North', 3, 2024, 230000.00),
    (10, 'Phone',   'South', 1, 2024, 160000.00),
    (11, 'Phone',   'South', 2, 2024, 195000.00),
    (12, 'Phone',   'South', 3, 2024, 215000.00)
ON CONFLICT(sale_id) DO NOTHING;

INSERT INTO quarterly_budget (department, q1_budget, q2_budget, q3_budget, q4_budget) VALUES
    ('Engineering',  500000.00, 550000.00, 480000.00, 620000.00),
    ('Marketing',    200000.00, 350000.00, 280000.00, 400000.00),
    ('Sales',        300000.00, 420000.00, 390000.00, 500000.00),
    ('HR',           100000.00, 110000.00,  95000.00, 120000.00)
ON CONFLICT(department) DO NOTHING;

-- Module 03: API Events
INSERT INTO api_events (event_id, event_type, source, received_at, payload) VALUES
    (1, 'order.created', 'shopify', '2024-01-15 10:30:00', '{"order_id": "ORD-001", "customer": {"id": 1001, "name": "Alice Johnson", "email": "alice@example.com", "tier": "premium"}, "items": [{"sku": "LAPTOP-X1", "qty": 1, "price": 1299.99}], "total": 1299.99, "currency": "USD", "shipping": {"method": "express", "days": 2}, "tags": ["vip"]}'),
    (2, 'order.created', 'shopify', '2024-01-15 11:00:00', '{"order_id": "ORD-002", "customer": {"id": 1002, "name": "Bob Smith", "email": "bob@example.com", "tier": "standard"}, "items": [{"sku": "PHONE-S22", "qty": 1, "price": 899.00}], "total": 899.00, "currency": "USD", "shipping": {"method": "standard", "days": 5}, "tags": ["new"]}')
ON CONFLICT(event_id) DO NOTHING;

-- Module 04: Customers & Orders & Tags
INSERT INTO customers (customer_id, customer_name, country, signup_date, segment) VALUES
    (1, 'Alice Johnson',  'US',  '2022-01-10', 'premium'),
    (2, 'Bob Smith',      'UK',  '2022-03-15', 'standard'),
    (3, 'Carol Davis',    'US',  '2022-06-01', 'premium'),
    (4, 'Dave Wilson',    'CA',  '2023-01-20', 'trial'),
    (5, 'Eve Martinez',   'US',  '2023-04-10', 'standard')
ON CONFLICT(customer_id) DO NOTHING;

INSERT INTO orders (order_id, customer_id, order_date, product_name, amount, status) VALUES
    (101, 1, '2024-01-05', 'Laptop Pro',    2500.00, 'completed'),
    (102, 1, '2024-02-12', 'Wireless Mouse',  45.00, 'completed'),
    (103, 1, '2024-03-20', 'USB Hub',         35.00, 'completed'),
    (104, 1, '2024-04-08', 'Monitor 4K',    1200.00, 'completed'),
    (105, 2, '2024-01-18', 'Keyboard',       120.00, 'completed'),
    (106, 2, '2024-03-05', 'Laptop Pro',    2500.00, 'refunded'),
    (107, 2, '2024-05-22', 'Webcam',         180.00, 'completed')
ON CONFLICT(order_id) DO NOTHING;

INSERT INTO product_tags (product_id, product_name, tags_csv) VALUES
    (1, 'Wireless Headphones', 'electronics,portable,wireless,audio'),
    (2, 'USB-C Hub',           'electronics,accessories,connectivity')
ON CONFLICT(product_id) DO NOTHING;

-- Module 05: Daily Metrics
INSERT INTO daily_metrics (metric_id, metric_date, store_id, daily_revenue, transaction_cnt) VALUES
    (1,  '2024-01-01', 101, 1000.00, 50),
    (2,  '2024-01-02', 101, 1200.00, 55),
    (3,  '2024-01-03', 101,  800.00, 40),
    (4,  '2024-01-04', 101, 1500.00, 70)
ON CONFLICT(metric_id) DO NOTHING;

-- Module 06: Ledger Transactions
INSERT INTO ledger_transactions (txn_id, account_id, txn_date, txn_amount, txn_type) VALUES
    (1,  1001, '2024-01-01',  500.00, 'CREDIT'),
    (2,  1001, '2024-01-02', -150.00, 'DEBIT'),
    (3,  1001, '2024-01-03',  200.00, 'CREDIT')
ON CONFLICT(txn_id) DO NOTHING;

-- Module 07: User Logins & Invoices & Server Status
INSERT INTO user_logins (login_id, user_id, login_date) VALUES
    (1,  101, '2024-01-01'),
    (2,  101, '2024-01-02'),
    (3,  101, '2024-01-03'),
    (4,  101, '2024-01-06')
ON CONFLICT(login_id) DO NOTHING;

INSERT INTO invoice_sequence (seq_id, status) VALUES
    (1001, 'ISSUED'), (1002, 'ISSUED'), (1003, 'ISSUED'), (1006, 'ISSUED')
ON CONFLICT(seq_id) DO NOTHING;

INSERT INTO server_status (event_time, server_id, status) VALUES
    ('2024-01-01 10:00:00', 1, 'UP'),
    ('2024-01-01 10:05:00', 1, 'DOWN')
ON CONFLICT(event_time) DO NOTHING;

-- Module 08: Product Daily Sales
INSERT INTO product_daily_sales (sale_date, product_id, units_sold, unit_price) VALUES
    ('2024-01-01', 501, 10, 100.00),
    ('2024-01-02', 501, 15, 100.00),
    ('2024-01-04', 501, 20, 105.00)
ON CONFLICT(sale_date, product_id) DO NOTHING;

-- Module 09: Target & Staging Customers
INSERT INTO target_customers (customer_id, full_name, email, tier, updated_at) VALUES
    (1, 'Alice Johnson', 'alice@example.com', 'SILVER', '2024-01-01 10:00:00'),
    (2, 'Bob Smith',     'bob@example.com',   'BRONZE', '2024-01-01 10:00:00')
ON CONFLICT(customer_id) DO NOTHING;

INSERT INTO staging_customers (customer_id, full_name, email, tier, updated_at) VALUES
    (1, 'Alice Johnson', 'alice_new@example.com', 'GOLD',   '2024-01-02 12:00:00'),
    (3, 'Charlie Brown', 'charlie@example.com',   'BRONZE', '2024-01-02 12:00:00')
ON CONFLICT(customer_id) DO NOTHING;

-- Module 10: Regional Sales
INSERT INTO regional_sales (sales_id, year, region, category, amount) VALUES
    (1, 2024, 'NORTH', 'ELECTRONICS', 50000.00),
    (2, 2024, 'SOUTH', 'FURNITURE',   30000.00)
ON CONFLICT(sales_id) DO NOTHING;

-- Module 11: SCD Type 2
INSERT INTO dim_employee_scd2 (employee_id, employee_name, department, salary, valid_from, valid_to, is_current) VALUES
    (101, 'Alice Smith', 'Engineering', 90000.00, '2024-01-01 00:00:00', '9999-12-31 23:59:59', 1)
ON CONFLICT DO NOTHING;

INSERT INTO staging_employee_updates (employee_id, employee_name, department, salary, effective_ts) VALUES
    (101, 'Alice Smith', 'Product Tech', 110000.00, '2024-06-01 00:00:00')
ON CONFLICT(employee_id) DO NOTHING;

-- Module 12: Data Vault
INSERT INTO hub_customer (hk_customer_id, customer_id, load_date, record_source) VALUES
    ('HK_CUST_1001', 1001, '2024-01-01 00:00:00', 'CRM_POSTGRES')
ON CONFLICT(hk_customer_id) DO NOTHING;

INSERT INTO hub_store (hk_store_id, store_id, load_date, record_source) VALUES
    ('HK_STORE_50', 50, '2024-01-01 00:00:00', 'POS_SYSTEM')
ON CONFLICT(hk_store_id) DO NOTHING;

INSERT INTO link_customer_store (hk_link_cust_store, hk_customer_id, hk_store_id, load_date, record_source) VALUES
    ('HK_LINK_1001_50', 'HK_CUST_1001', 'HK_STORE_50', '2024-01-02 10:00:00', 'POS_SYSTEM')
ON CONFLICT(hk_link_cust_store) DO NOTHING;

INSERT INTO sat_customer_profile (hk_customer_id, load_date, customer_name, email, address, hash_diff, record_source) VALUES
    ('HK_CUST_1001', '2024-01-01 00:00:00', 'Alice Johnson', 'alice@old.com', '123 Main St', 'HASH_V1', 'CRM_POSTGRES')
ON CONFLICT(hk_customer_id, load_date) DO NOTHING;

-- Module 13: Web Logs
INSERT INTO web_logs (log_id, user_id, url_path, status_code, response_ms, created_at) VALUES
    (1, 101, '/home',     200, 45.2, '2024-01-01 10:00:00'),
    (2, 102, '/products', 500, 850.0,'2024-01-01 10:06:00')
ON CONFLICT(log_id) DO NOTHING;

-- Module 14: Partitioned Orders
INSERT INTO partitioned_orders (order_id, order_date, country_code, total_amount) VALUES
    (101, '2024-01-15', 'US', 250.00),
    (102, '2024-02-10', 'CA', 320.00)
ON CONFLICT(order_id) DO NOTHING;

-- Module 15: Orders Raw
INSERT INTO orders_raw (order_id, customer_id, order_date, amount, status) VALUES
    (1, 101, '2024-01-15', 500.00, 'COMPLETED'),
    (2, 101, '2024-01-16', 300.00, 'COMPLETED')
ON CONFLICT(order_id) DO NOTHING;

-- Module 16: Clickstream Events
INSERT INTO clickstream_events (event_id, user_id, event_time, page_name) VALUES
    (1, 101, '2024-01-01 10:00:00', 'home'),
    (2, 101, '2024-01-01 10:05:00', 'cart')
ON CONFLICT(event_id) DO NOTHING;

-- Module 17: User Cohorts & Activity
INSERT INTO user_cohort_signups (user_id, signup_date) VALUES
    (1, '2024-01-10'),
    (2, '2024-01-15')
ON CONFLICT(user_id) DO NOTHING;

INSERT INTO user_monthly_activity (activity_id, user_id, activity_date) VALUES
    (101, 1, '2024-01-12'),
    (102, 1, '2024-02-10')
ON CONFLICT(activity_id) DO NOTHING;

-- Module 18: CDC Orders Stream
INSERT INTO cdc_orders_stream (cdc_id, order_id, customer_id, amount, status, cdc_op, lsn_seq, cdc_timestamp) VALUES
    (1, 501, 10, 100.00, 'PENDING',   'I', 1001, '2024-01-01 10:00:00'),
    (2, 501, 10, 100.00, 'SHIPPED',   'U', 1002, '2024-01-01 10:05:00')
ON CONFLICT(cdc_id) DO NOTHING;

-- Module 19: Order Basket Items
INSERT INTO order_basket_items (basket_id, order_id, product_name) VALUES
    (1, 1001, 'Laptop'), (2, 1001, 'Mouse'), (3, 1002, 'Laptop'), (4, 1002, 'Mouse')
ON CONFLICT(basket_id) DO NOTHING;

-- Module 20: Raw Staging Transactions
INSERT INTO stg_raw_transactions (raw_id, txn_id, customer_id, amount, txn_timestamp) VALUES
    (1, 101, 1001, 150.00, '2024-01-01 10:00:00'),
    (2, 101, 1001, 175.00, '2024-01-01 10:05:00')
ON CONFLICT(raw_id) DO NOTHING;
