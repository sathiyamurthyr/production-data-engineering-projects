-- Seed Data for Project 02

INSERT INTO dim_departments VALUES 
(101, 'Data Engineering', 'Sathiya Murthy', 'Building A'),
(102, 'Data Science', 'Jane Doe', 'Building A'),
(103, 'DevOps & Platform', 'John Smith', 'Building B'),
(104, 'Analytics Engineering', 'Alice Johnson', 'Building A');

INSERT INTO dim_employees VALUES
(1, 'Sathiya', 'Murthy', 'sathiya@example.com', 101, 145000.00, NULL, '2022-01-15'),
(2, 'Bob', 'Jones', 'bob@example.com', 101, 115000.00, 1, '2023-03-01'),
(3, 'Charlie', 'Brown', 'charlie@example.com', 102, 120000.00, 1, '2023-06-10'),
(4, 'Diana', 'Prince', 'diana@example.com', 104, 125000.00, 1, '2024-01-05'),
(5, 'Ethan', 'Hunt', 'ethan@example.com', 103, 110000.00, 2, '2024-02-01');

INSERT INTO dim_customers (customer_id, first_name, last_name, email, city, state, country, effective_start_date, is_current) VALUES
('CUST001', 'Alice', 'Smith', 'alice@example.com', 'New York', 'NY', 'USA', '2024-01-01', 1),
('CUST002', 'Bob', 'Taylor', 'bob.t@example.com', 'San Francisco', 'CA', 'USA', '2024-01-15', 1),
('CUST003', 'Carol', 'Danvers', 'carol@example.com', 'Seattle', 'WA', 'USA', '2024-02-01', 1),
('CUST004', 'David', 'Miller', 'david@example.com', 'Austin', 'TX', 'USA', '2024-02-10', 1);

INSERT INTO dim_products (product_id, product_name, category, subcategory, unit_price, cost_price) VALUES
('PROD001', 'MacBook Pro 16', 'Electronics', 'Laptops', 2499.99, 1800.00),
('PROD002', 'Dell XPS 15', 'Electronics', 'Laptops', 1899.99, 1350.00),
('PROD003', 'Monitor 4K', 'Electronics', 'Displays', 499.99, 300.00),
('PROD004', 'Ergonomic Chair', 'Furniture', 'Chairs', 299.99, 150.00);

INSERT INTO fact_sales (transaction_id, customer_key, product_key, sale_date, quantity, gross_amount, discount_amount, net_amount, status) VALUES
('TXN1001', 1, 1, '2026-07-01', 1, 2499.99, 100.00, 2399.99, 'COMPLETED'),
('TXN1002', 1, 3, '2026-07-02', 2, 999.98, 0.00, 999.98, 'COMPLETED'),
('TXN1003', 2, 2, '2026-07-03', 1, 1899.99, 50.00, 1849.99, 'COMPLETED'),
('TXN1004', 3, 4, '2026-07-04', 4, 1199.96, 100.00, 1099.96, 'COMPLETED'),
('TXN1005', 4, 1, '2026-07-05', 1, 2499.99, 0.00, 2499.99, 'FAILED');

INSERT INTO fact_orders (order_number, customer_key, order_date, order_status, total_amount) VALUES
('ORD100', 1, '2026-07-01', 'DELIVERED', 2399.99),
('ORD101', 2, '2026-07-03', 'SHIPPED', 1849.99),
('ORD102', 3, '2026-07-04', 'PROCESSING', 1099.96);

INSERT INTO fact_payments (payment_reference, order_id, payment_date, payment_method, payment_amount, status) VALUES
('PAY500', 1, '2026-07-01', 'CREDIT_CARD', 2399.99, 'SUCCESS'),
('PAY501', 2, '2026-07-03', 'PAYPAL', 1849.99, 'SUCCESS'),
('PAY502', 3, '2026-07-04', 'WIRE_TRANSFER', 1099.96, 'PENDING');

INSERT INTO fact_invoices (invoice_number, customer_key, invoice_date, due_date, invoice_amount, paid_amount, status) VALUES
('INV800', 1, '2026-07-01', '2026-07-31', 2399.99, 2399.99, 'PAID'),
('INV801', 2, '2026-07-03', '2026-08-03', 1849.99, 0.00, 'UNPAID');

INSERT INTO fact_transactions (account_id, txn_timestamp, txn_type, amount, currency) VALUES
('ACC100', '2026-07-20T10:00:00Z', 'DEPOSIT', 5000.00, 'USD'),
('ACC100', '2026-07-20T11:30:00Z', 'WITHDRAWAL', 200.00, 'USD'),
('ACC200', '2026-07-20T12:00:00Z', 'DEPOSIT', 10000.00, 'USD');

INSERT INTO fact_inventory (product_key, warehouse_location, stock_quantity, reorder_level, last_updated) VALUES
(1, 'US-East-1', 45, 10, '2026-07-20'),
(2, 'US-East-1', 30, 5, '2026-07-20'),
(3, 'US-West-2', 120, 20, '2026-07-20'),
(4, 'US-Central', 85, 15, '2026-07-20');

INSERT INTO healthcare_claims (patient_id, provider_id, diagnosis_code, claim_amount, approved_amount, claim_date, claim_status) VALUES
('PAT10', 'PRV50', 'E11.9', 1500.00, 1200.00, '2026-07-01', 'APPROVED'),
('PAT11', 'PRV51', 'I10', 800.00, 800.00, '2026-07-02', 'APPROVED');

INSERT INTO banking_transactions (account_number, transaction_type, amount, balance_after, transaction_date) VALUES
('ACC1001', 'CREDIT', 1500.00, 6500.00, '2026-07-20'),
('ACC1001', 'DEBIT', 200.00, 6300.00, '2026-07-20');

INSERT INTO iot_sensor_data (device_id, metric_name, reading_value, reading_time) VALUES
('DEV_TEMP_01', 'temperature_celsius', 24.5, '2026-07-20T12:00:00Z'),
('DEV_TEMP_01', 'temperature_celsius', 25.1, '2026-07-20T12:01:00Z'),
('DEV_TEMP_01', 'temperature_celsius', 24.8, '2026-07-20T12:02:00Z');

INSERT INTO audit_logs (pipeline_name, table_name, records_inserted, records_updated, status, executed_at) VALUES
('daily_sales_etl', 'fact_sales', 5, 0, 'SUCCESS', '2026-07-20T02:00:00Z');

INSERT INTO stg_sales_incremental VALUES
('TXN1006', 'CUST001', 'PROD003', '2026-07-20', 1, 499.99, 'COMPLETED');
