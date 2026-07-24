-- Sample Customer Dataset for Data Engineering Examples
-- Business Use Case: Customer dimension in data warehouse

DROP TABLE IF EXISTS raw_customers;
CREATE TABLE raw_customers (
    customer_id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    signup_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

INSERT INTO raw_customers (customer_id, first_name, last_name, email, phone, city, state, country, postal_code, signup_date, status) VALUES
(1, 'John', 'Smith', 'john.smith@email.com', '555-0101', 'New York', 'NY', 'USA', '10001', '2023-01-15', 'active'),
(2, 'Emily', 'Johnson', 'emily.johnson@email.com', '555-0102', 'Toronto', 'ON', 'Canada', 'M5V 1A1', '2023-02-20', 'active'),
(3, 'Michael', 'Brown', 'michael.brown@email.com', '555-0103', 'London', 'UK', 'UK', 'SW1A 1AA', '2023-03-10', 'inactive'),
(4, 'Sarah', 'Davis', 'sarah.davis@email.com', '555-0104', 'Sydney', 'NSW', 'Australia', '2000', '2023-01-25', 'active'),
(5, 'David', 'Wilson', 'david.wilson@email.com', NULL, 'Los Angeles', 'CA', 'USA', '90001', '2023-04-05', 'active');

-- Orders table for JOIN examples
DROP TABLE IF EXISTS raw_orders;
CREATE TABLE raw_orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES raw_customers(customer_id),
    order_date DATE NOT NULL,
    order_status VARCHAR(20),
    total_amount DECIMAL(10,2),
    payment_method VARCHAR(30),
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO raw_orders (order_id, customer_id, order_date, order_status, total_amount, payment_method) VALUES
(1001, 1, '2024-01-15', 'completed', 150.50, 'credit_card'),
(1002, 1, '2024-01-20', 'pending', 75.25, 'paypal'),
(1003, 2, '2024-01-16', 'completed', 250.00, 'credit_card'),
(1004, 3, '2024-01-17', 'cancelled', 50.00, 'credit_card'),
(1005, 5, '2024-01-18', 'completed', 300.75, 'bank_transfer'),
(1006, 1, '2024-02-01', 'completed', 200.00, 'credit_card');

-- Products table
DROP TABLE IF EXISTS raw_products;
CREATE TABLE raw_products (
    product_id INTEGER PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10,2),
    stock_quantity INTEGER,
    supplier_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO raw_products (product_id, product_name, category, price, stock_quantity, supplier_id) VALUES
(101, 'Laptop Pro 15', 'Electronics', 1299.99, 50, 1),
(102, 'Wireless Mouse', 'Electronics', 29.99, 200, 1),
(103, 'Office Chair', 'Furniture', 249.99, 100, 2),
(104, 'Desk Lamp', 'Furniture', 49.99, 150, 2),
(105, 'USB-C Cable', 'Electronics', 19.99, 500, 3);