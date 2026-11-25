-- =============================================================================
-- Module 19: Market Basket Analysis and Association Rules Mining
-- =============================================================================
-- File        : m19_market_basket_analysis.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Market Basket Analysis discovers items frequently purchased together in single transaction baskets.
--
-- Statistical Metrics:
--   1. Support (A, B)    : Frequency of transactions containing both Item A and Item B.
--   2. Confidence (A -> B): `Support(A, B) / Support(A)` — conditional probability of buying B given A.
--   3. Lift (A, B)       : `Confidence(A -> B) / Support(B)` — strength of association compared to random chance (> 1 indicates positive association).

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • E-Commerce Checkout  : "Frequently Bought Together" product recommendation widgets
-- • Retail Merchandising : Optimizing physical grocery store shelf layout and cross-category promotions
-- • Subscription Bundles : Packaging streaming software or insurance add-on services

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS order_basket_items (
    basket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL,
    product_name TEXT NOT NULL
);

INSERT INTO order_basket_items (order_id, product_name)
VALUES
    (1001, 'Laptop'),    (1001, 'Mouse'),      (1001, 'Backpack'),
    (1002, 'Laptop'),    (1002, 'Mouse'),
    (1003, 'Laptop'),    (1003, 'Backpack'),
    (1004, 'Mouse'),     (1004, 'Mousepad'),
    (1005, 'Laptop'),    (1005, 'Mouse'),      (1005, 'Mousepad')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- QUERY 1: Co-Occurrence Product Pairs Frequency (Support Count)
-- =============================================================================

SELECT
    i1.product_name AS item_a,
    i2.product_name AS item_b,
    COUNT(DISTINCT i1.order_id) AS pair_support_count
FROM order_basket_items i1
JOIN order_basket_items i2
    ON i1.order_id = i2.order_id
   AND i1.product_name < i2.product_name -- Prevent self-pairs & canonicalize order
GROUP BY i1.product_name, i2.product_name
ORDER BY pair_support_count DESC;

-- Expected Output:
-- item_a | item_b | pair_support_count
-- Laptop | Mouse  | 3
-- Backpack| Laptop| 2
-- Mouse  | Mousepad| 2

-- =============================================================================
-- QUERY 2: Full Association Metrics — Support, Confidence, and Lift
-- =============================================================================

WITH total_baskets AS (
    SELECT COUNT(DISTINCT order_id) AS total_orders FROM order_basket_items
),
item_support AS (
    SELECT
        product_name,
        COUNT(DISTINCT order_id) AS item_order_count
    FROM order_basket_items
    GROUP BY product_name
),
pair_support AS (
    SELECT
        i1.product_name AS item_a,
        i2.product_name AS item_b,
        COUNT(DISTINCT i1.order_id) AS pair_order_count
    FROM order_basket_items i1
    JOIN order_basket_items i2
        ON i1.order_id = i2.order_id
       AND i1.product_name <> i2.product_name
    GROUP BY i1.product_name, i2.product_name
)
SELECT
    p.item_a,
    p.item_b,
    p.pair_order_count AS support_count,
    ROUND(100.0 * p.pair_order_count / (SELECT total_orders FROM total_baskets), 2) AS support_pct,
    ROUND(100.0 * p.pair_order_count / s1.item_order_count, 2) AS confidence_pct,
    ROUND(
        (1.0 * p.pair_order_count / s1.item_order_count) /
        (1.0 * s2.item_order_count / (SELECT total_orders FROM total_baskets)), 2
    ) AS lift_score
FROM pair_support p
JOIN item_support s1 ON p.item_a = s1.product_name
JOIN item_support s2 ON p.item_b = s2.product_name
WHERE p.pair_order_count >= 2
ORDER BY lift_score DESC, confidence_pct DESC;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Self-joining `order_basket_items` can explode to $O(N^2)$ rows for large baskets. Pre-filter low-frequency items before joining.
-- 2. Index `(order_id, product_name)` is mandatory for sub-second self-join performance.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Use predicate condition `i1.product_name < i2.product_name` to eliminate duplicate reverse pairs `(A, B)` vs `(B, A)`.
-- TIP 2: Limit analysis to top 500 popular items to prevent combinatorial explosion in warehouse memory.
-- TIP 3: In Snowflake / BigQuery, pre-aggregate item arrays using `ARRAY_AGG` and use `ARRAY_INTERSECT` for fast pair evaluation.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Self-joining on `i1.product_name <> i2.product_name` without canonical order comparison (`<`), doubling memory and output size.
-- MISTAKE 2: Including orders containing only a single item in pair matching calculations.
-- MISTAKE 3: Interpreting high confidence without evaluating Lift (item B might be a globally popular item bought by everyone regardless of item A).

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the definition of Lift in Market Basket Analysis and how is it interpreted?
--     A: Lift measures how much more often items A and B are bought together compared to if they were statistically independent. `Lift > 1` indicates positive association; `Lift = 1` indicates independence; `Lift < 1` indicates negative substitution association.
-- Q2: How do you prevent calculating duplicate reverse pairs `(Mouse, Laptop)` vs `(Laptop, Mouse)` in SQL?
--     A: Use the strict inequality predicate `JOIN ... ON i1.order_id = i2.order_id AND i1.product_name < i2.product_name`.
-- Q3: What is the computational complexity of pair-wise self-joins in SQL Market Basket analysis?
--     A: O(K^2) per order basket where K is number of items in the basket.
-- Q4: What is Confidence in association rules mining?
--     A: The proportion of orders containing Item A that also contain Item B: `Support(A, B) / Support(A)`.
-- Q5: How do you scale Market Basket SQL queries to handle 100 million transactions?
--     A: Pre-filter input table to retain only items meeting minimum support thresholds (Apriori pruning principle) before self-joining.
