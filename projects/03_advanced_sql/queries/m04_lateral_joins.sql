-- =============================================================================
-- Module 04: Lateral Joins — Row-Level Correlated Calculations
-- =============================================================================
-- File        : m04_lateral_joins.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- A LATERAL join (CROSS APPLY in SQL Server) allows a subquery in the FROM
-- clause to reference columns from tables listed BEFORE it in the same FROM
-- clause. Think of it as a "for each row, run this subquery using that row."
--
-- Without LATERAL: subqueries in FROM are independent — cannot see outer table columns
-- With LATERAL:    subquery runs once per row of the outer table, using its values
--
-- Key forms:
--   CROSS JOIN LATERAL       : Like INNER JOIN — drops rows where lateral returns nothing
--   LEFT JOIN LATERAL ... ON TRUE : Like LEFT JOIN — keeps rows even if lateral empty

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Top-N per group: Best 3 orders per customer
-- • Unnesting arrays: Convert JSON/array columns into rows (M03 used this)
-- • Row-level calculations: Apply a formula using values from the same row
-- • Sampling: Random sample of N rows per partition
-- • String splitting: Split CSV column values into rows

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS customers (
    customer_id   INT          PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    country       VARCHAR(50)  NOT NULL,
    signup_date   DATE         NOT NULL,
    segment       VARCHAR(20)  NOT NULL  -- 'premium', 'standard', 'trial'
);

CREATE TABLE IF NOT EXISTS orders (
    order_id      INT           PRIMARY KEY,
    customer_id   INT           NOT NULL REFERENCES customers(customer_id),
    order_date    DATE          NOT NULL,
    product_name  VARCHAR(100)  NOT NULL,
    amount        NUMERIC(10,2) NOT NULL,
    status        VARCHAR(20)   NOT NULL  -- 'completed', 'refunded', 'pending'
);

INSERT INTO customers (customer_id, customer_name, country, signup_date, segment)
VALUES
    (1, 'Alice Johnson',  'US',  '2022-01-10', 'premium'),
    (2, 'Bob Smith',      'UK',  '2022-03-15', 'standard'),
    (3, 'Carol Davis',    'US',  '2022-06-01', 'premium'),
    (4, 'Dave Wilson',    'CA',  '2023-01-20', 'trial'),
    (5, 'Eve Martinez',   'US',  '2023-04-10', 'standard')
ON CONFLICT DO NOTHING;

INSERT INTO orders (order_id, customer_id, order_date, product_name, amount, status)
VALUES
    (101, 1, '2024-01-05', 'Laptop Pro',    2500.00, 'completed'),
    (102, 1, '2024-02-12', 'Wireless Mouse',  45.00, 'completed'),
    (103, 1, '2024-03-20', 'USB Hub',         35.00, 'completed'),
    (104, 1, '2024-04-08', 'Monitor 4K',    1200.00, 'completed'),
    (105, 2, '2024-01-18', 'Keyboard',       120.00, 'completed'),
    (106, 2, '2024-03-05', 'Laptop Pro',    2500.00, 'refunded'),
    (107, 2, '2024-05-22', 'Webcam',         180.00, 'completed'),
    (108, 3, '2024-01-30', 'iPad',           800.00, 'completed'),
    (109, 3, '2024-04-15', 'AirPods',        250.00, 'completed'),
    (110, 3, '2024-06-01', 'MacBook',       1800.00, 'completed'),
    (111, 4, '2024-02-08', 'Pen Drive',       15.00, 'completed'),
    (112, 5, '2024-03-14', 'Monitor 4K',    1200.00, 'pending'),
    (113, 5, '2024-05-20', 'SSD Drive',      180.00, 'completed')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- QUERY 1: Top-N Per Group — Top 2 Orders Per Customer
-- =============================================================================
-- Without LATERAL, this requires ROW_NUMBER() or complex self-joins.
-- LATERAL makes it elegant and readable.

SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    top_orders.order_id,
    top_orders.product_name,
    top_orders.amount,
    top_orders.order_date,
    top_orders.order_rank

FROM customers c

-- CROSS JOIN LATERAL: runs the subquery for EACH row of customers
-- If a customer has 0 orders, they are excluded (INNER join semantics)
CROSS JOIN LATERAL (
    SELECT
        o.order_id,
        o.product_name,
        o.amount,
        o.order_date,
        ROW_NUMBER() OVER (ORDER BY o.amount DESC) AS order_rank
    FROM orders o
    WHERE
        o.customer_id = c.customer_id    -- ← Referencing outer table column!
        AND o.status = 'completed'
    ORDER BY o.amount DESC
    LIMIT 2
) AS top_orders

ORDER BY c.customer_id, top_orders.order_rank;

-- Expected Output (Top 2 completed orders per customer by amount):
-- customer_id | customer_name  | order_id | product_name | amount  | rank
-- 1           | Alice Johnson  | 101      | Laptop Pro   | 2500.00 | 1
-- 1           | Alice Johnson  | 104      | Monitor 4K   | 1200.00 | 2
-- 2           | Bob Smith      | 107      | Webcam       | 180.00  | 1
-- 2           | Bob Smith      | 105      | Keyboard     | 120.00  | 2

-- =============================================================================
-- QUERY 2: LEFT JOIN LATERAL — Keep All Customers Including Those With No Orders
-- =============================================================================

SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    COALESCE(latest.order_date::TEXT, 'No orders')    AS last_order_date,
    COALESCE(latest.amount::TEXT, '0.00')             AS last_order_amount,
    COALESCE(latest.product_name, 'N/A')              AS last_product

FROM customers c

LEFT JOIN LATERAL (
    SELECT
        o.order_date,
        o.amount,
        o.product_name
    FROM orders o
    WHERE o.customer_id = c.customer_id
    ORDER BY o.order_date DESC
    LIMIT 1                                            -- Most recent order only
) AS latest ON TRUE                                    -- ON TRUE = always keep left row

ORDER BY c.customer_id;

-- =============================================================================
-- QUERY 3: LATERAL for Per-Row Calculations — Running Percentile
-- =============================================================================
-- For each customer, calculate their order amounts relative to their own avg

SELECT
    c.customer_id,
    c.customer_name,
    order_stats.total_orders,
    order_stats.total_spent,
    order_stats.avg_order_amount,
    order_stats.max_order_amount,
    order_stats.min_order_amount,
    CASE
        WHEN order_stats.total_orders >= 3 THEN 'High Activity'
        WHEN order_stats.total_orders >= 2 THEN 'Medium Activity'
        ELSE 'Low Activity'
    END AS activity_segment

FROM customers c

-- Aggregate stats computed per customer using LATERAL
CROSS JOIN LATERAL (
    SELECT
        COUNT(*)                    AS total_orders,
        SUM(o.amount)               AS total_spent,
        ROUND(AVG(o.amount), 2)     AS avg_order_amount,
        MAX(o.amount)               AS max_order_amount,
        MIN(o.amount)               AS min_order_amount
    FROM orders o
    WHERE o.customer_id = c.customer_id
) AS order_stats

ORDER BY order_stats.total_spent DESC;

-- =============================================================================
-- QUERY 4: LATERAL with generate_series — Generating Date Spines Per Customer
-- =============================================================================
-- For each customer, generate a date for every month since signup.
-- Useful for filling gaps in time series (customers with no activity in a month).

SELECT
    c.customer_id,
    c.customer_name,
    c.signup_date,
    date_spine.month_start,
    TO_CHAR(date_spine.month_start, 'YYYY-MM') AS month_label,
    COALESCE(mo.monthly_revenue, 0)            AS monthly_revenue

FROM customers c

-- Generate one row per month from signup_date to today, per customer
CROSS JOIN LATERAL (
    SELECT
        gs::DATE AS month_start
    FROM generate_series(
        DATE_TRUNC('month', c.signup_date),       -- Start: customer's signup month
        DATE_TRUNC('month', CURRENT_DATE),         -- End: current month
        INTERVAL '1 month'
    ) AS gs
) AS date_spine

-- Left join actual orders to find revenue, NULL where no orders exist
LEFT JOIN (
    SELECT
        customer_id,
        DATE_TRUNC('month', order_date)::DATE   AS month_start,
        SUM(amount)                             AS monthly_revenue
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id, DATE_TRUNC('month', order_date)::DATE
) mo
    ON  mo.customer_id = c.customer_id
    AND mo.month_start = date_spine.month_start

WHERE c.customer_id = 1   -- Filter to Alice for example output
ORDER BY date_spine.month_start;

-- =============================================================================
-- QUERY 5: LATERAL for String Splitting (CSV column to rows)
-- =============================================================================
-- Simulate a column containing comma-separated tags

CREATE TABLE IF NOT EXISTS product_tags (
    product_id   INT     PRIMARY KEY,
    product_name TEXT    NOT NULL,
    tags_csv     TEXT    NOT NULL   -- e.g., "electronics,portable,wireless"
);

INSERT INTO product_tags (product_id, product_name, tags_csv)
VALUES
    (1, 'Wireless Headphones', 'electronics,portable,wireless,audio'),
    (2, 'USB-C Hub',           'electronics,accessories,connectivity'),
    (3, 'Laptop Stand',        'accessories,ergonomic,portable')
ON CONFLICT DO NOTHING;

SELECT
    p.product_id,
    p.product_name,
    TRIM(tag.value)     AS tag,
    tag.tag_position
FROM product_tags p
CROSS JOIN LATERAL (
    SELECT
        UNNEST(STRING_TO_ARRAY(p.tags_csv, ','))    AS value,
        GENERATE_SUBSCRIPTS(STRING_TO_ARRAY(p.tags_csv, ','), 1) AS tag_position
) AS tag
ORDER BY p.product_id, tag.tag_position;

-- =============================================================================
-- QUERY 6: LATERAL with Window Function — Percentile Within Customer Group
-- =============================================================================

SELECT
    c.customer_id,
    c.customer_name,
    o.order_id,
    o.amount,
    stats.percentile_25,
    stats.percentile_75,
    CASE
        WHEN o.amount >= stats.percentile_75 THEN 'High Value'
        WHEN o.amount >= stats.percentile_25 THEN 'Mid Value'
        ELSE 'Low Value'
    END AS order_value_band

FROM customers c
JOIN orders o ON o.customer_id = c.customer_id

-- LATERAL computes percentiles using only this customer's order history
CROSS JOIN LATERAL (
    SELECT
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY o2.amount) AS percentile_25,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY o2.amount) AS percentile_75
    FROM orders o2
    WHERE o2.customer_id = c.customer_id
        AND o2.status = 'completed'
) AS stats

WHERE o.status = 'completed'
ORDER BY c.customer_id, o.amount DESC;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. LATERAL runs the subquery N times — once per outer row.
--    Ensure the inner query is fast with proper indexes on join conditions.
-- 2. Index on orders(customer_id, order_date DESC) is critical for LATERAL
--    queries that ORDER + LIMIT per customer.
-- 3. For Top-N per group at scale, compare LATERAL vs WINDOW FUNCTION approach:
--    Window: better when you need all rows with rank; LATERAL: better for LIMIT
-- 4. PostgreSQL can sometimes use "index scan with limit" inside LATERAL loops,
--    making LATERAL + LIMIT extremely efficient vs. self-join approaches.

CREATE INDEX IF NOT EXISTS idx_orders_customer_date
    ON orders(customer_id, order_date DESC);

CREATE INDEX IF NOT EXISTS idx_orders_customer_amount
    ON orders(customer_id, amount DESC);

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Using CROSS JOIN LATERAL when you should use LEFT JOIN LATERAL
--            — loses customers/rows that have no matching subquery results
-- MISTAKE 2: Missing the index on the correlated join column (customer_id)
-- MISTAKE 3: Not adding ON TRUE for LEFT JOIN LATERAL — syntax error
-- MISTAKE 4: Running expensive subqueries without LIMIT inside LATERAL loops
-- MISTAKE 5: Confusing LATERAL (PostgreSQL/ANSI) with APPLY (SQL Server only)

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is a LATERAL join and how does it differ from a regular subquery?
--     A: A LATERAL subquery can reference columns from tables listed before it
--        in the FROM clause. A regular subquery in FROM is independent. LATERAL
--        is evaluated once per outer row, enabling row-level correlated logic.

-- Q2: How would you implement Top-3 orders per customer without window functions?
--     A: Use LATERAL: for each customer, SELECT ... FROM orders WHERE
--        customer_id = c.customer_id ORDER BY amount DESC LIMIT 3.

-- Q3: What is the difference between CROSS JOIN LATERAL and LEFT JOIN LATERAL?
--     A: CROSS JOIN LATERAL behaves like INNER JOIN — if the lateral subquery
--        returns 0 rows, the outer row is excluded. LEFT JOIN LATERAL ... ON TRUE
--        keeps the outer row and fills lateral columns with NULL.

-- Q4: When would you use LATERAL over ROW_NUMBER() window function?
--     A: Use LATERAL when: (1) you need LIMIT inside the lateral subquery,
--        (2) the subquery is complex and benefits from isolation,
--        (3) you're calling a set-returning function (like generate_series).
--        Use ROW_NUMBER when: you need the rank value itself, or you want
--        all rows visible to window for PARTITION BY.

-- Q5: Is CROSS JOIN LATERAL the same as a correlated subquery in the SELECT list?
--     A: Similar but not identical. A SELECT list subquery returns only one value
--        (scalar). LATERAL can return multiple columns and multiple rows,
--        making it more versatile for Top-N and set-returning scenarios.
