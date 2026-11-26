-- =============================================================================
-- Module 16: User Clickstream Sessionization and Funnel Analysis
-- =============================================================================
-- File        : m16_sessionization_user_analytics.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Sessionization groups continuous streams of user interaction events into discrete "sessions".
-- A session terminates when user inactivity exceeds a specified threshold (e.g. 30 minutes / 1800 seconds).
--
-- Sessionization Pipeline Steps:
--   1. Compute time delta since previous event for the same user using `LAG(event_time)`.
--   2. Flag events where time delta > 30 minutes as `is_new_session = 1`.
--   3. Generate unique `session_id` using cumulative sum: `SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_time)`.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Product Analytics   : Average session duration, pages per session, and bounce rate tracking
-- • E-Commerce Funnels   : Checkout conversion drop-off rates by step (View Product -> Add to Cart -> Checkout -> Purchase)
-- • Security Auditing   : Identifying compromised accounts by analyzing irregular session hop patterns

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS clickstream_events (
    event_id    INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    event_time  TEXT NOT NULL,
    page_name   TEXT NOT NULL
);

INSERT INTO clickstream_events (event_id, user_id, event_time, page_name)
VALUES
    -- User 101 - Session 1
    (1,  101, '2024-01-01 10:00:00', 'home'),
    (2,  101, '2024-01-01 10:05:00', 'product_list'),
    (3,  101, '2024-01-01 10:12:00', 'cart'),
    -- User 101 - Session 2 (48 min gap > 30 min boundary)
    (4,  101, '2024-01-01 11:00:00', 'home'),
    (5,  101, '2024-01-01 11:02:00', 'checkout'),
    (6,  101, '2024-01-01 11:05:00', 'purchase_success'),
    -- User 102 - Session 1
    (7,  102, '2024-01-01 10:15:00', 'home'),
    (8,  102, '2024-01-01 10:18:00', 'product_list')
ON CONFLICT(event_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: Clickstream Event Sessionization
-- =============================================================================

WITH time_deltas AS (
    SELECT
        event_id,
        user_id,
        event_time,
        page_name,
        LAG(event_time) OVER (
            PARTITION BY user_id
            ORDER BY event_time
        ) AS prev_event_time
    FROM clickstream_events
),
session_flags AS (
    SELECT
        event_id,
        user_id,
        event_time,
        page_name,
        CASE
            WHEN prev_event_time IS NULL THEN 1
            -- Convert epoch difference or timestamp gap (30 mins = 1800s)
            -- In SQLite: (julianday(event_time) - julianday(prev_event_time)) * 86400 > 1800
            WHEN (JULIANDAY(event_time) - JULIANDAY(prev_event_time)) * 86400 > 1800 THEN 1
            ELSE 0
        END AS is_new_session
    FROM time_deltas
),
session_labeled AS (
    SELECT
        event_id,
        user_id,
        event_time,
        page_name,
        user_id || '_S' || SUM(is_new_session) OVER (
            PARTITION BY user_id
            ORDER BY event_time
        ) AS session_id
    FROM session_flags
)
SELECT
    session_id,
    user_id,
    MIN(event_time) AS session_start_time,
    MAX(event_time) AS session_end_time,
    ROUND((JULIANDAY(MAX(event_time)) - JULIANDAY(MIN(event_time))) * 1440, 2) AS session_duration_minutes,
    COUNT(*) AS total_pages_viewed
FROM session_labeled
GROUP BY session_id, user_id
ORDER BY user_id, session_start_time;

-- Expected Output:
-- session_id | user_id | session_start_time  | session_end_time    | duration_mins | total_pages
-- 101_S1     | 101     | 2024-01-01 10:00:00 | 2024-01-01 10:12:00 | 12.0          | 3
-- 101_S2     | 101     | 2024-01-01 11:00:00 | 2024-01-01 11:05:00 | 5.0           | 3
-- 102_S1     | 102     | 2024-01-01 10:15:00 | 2024-01-01 10:18:00 | 3.0           | 2

-- =============================================================================
-- QUERY 2: Conversion Funnel Drop-off Analysis
-- =============================================================================

WITH funnel_stages AS (
    SELECT
        user_id,
        MAX(CASE WHEN page_name = 'home' THEN 1 ELSE 0 END) AS hit_home,
        MAX(CASE WHEN page_name = 'product_list' THEN 1 ELSE 0 END) AS hit_product_list,
        MAX(CASE WHEN page_name = 'cart' THEN 1 ELSE 0 END) AS hit_cart,
        MAX(CASE WHEN page_name = 'checkout' THEN 1 ELSE 0 END) AS hit_checkout,
        MAX(CASE WHEN page_name = 'purchase_success' THEN 1 ELSE 0 END) AS hit_purchase
    FROM clickstream_events
    GROUP BY user_id
)
SELECT
    SUM(hit_home) AS step1_home_users,
    SUM(hit_product_list) AS step2_list_users,
    SUM(hit_cart) AS step3_cart_users,
    SUM(hit_checkout) AS step4_checkout_users,
    SUM(hit_purchase) AS step5_purchased_users,
    ROUND(100.0 * SUM(hit_purchase) / NULLIF(SUM(hit_home), 0), 2) AS overall_conversion_pct
FROM funnel_stages;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Indexing `(user_id, event_time)` is mandatory for sub-second window function evaluation across clickstream events.
-- 2. Partition clickstream tables by `event_date` to prune historical partitions when running daily sessionization.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Pre-calculate session IDs during stream processing (Apache Flink / Spark Streaming) when event volume exceeds billions of events per day.
-- TIP 2: Use `FIRST_VALUE(page_name)` and `LAST_VALUE(page_name)` over session windows to extract entry and exit pages.
-- TIP 3: Handle out-of-order event arrivals by sorting on exact microsecond event timestamps inside `OVER (ORDER BY event_time)`.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Using client-side timestamp strings without converting to normalized UTC timestamps (causes cross-timezone session splits).
-- MISTAKE 2: Setting static 30-minute session gaps for mobile apps where push notification re-engagement occurs across hours.
-- MISTAKE 3: Forgetting tie-breaker sorting columns when multiple events occur within the same millisecond.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: How do you implement 30-minute sessionization in SQL without custom procedural code?
--     A: Calculate time delta from previous event via `LAG()`, flag deltas > 30 minutes as `1`, and perform a running cumulative `SUM(flag) OVER (PARTITION BY user_id ORDER BY event_time)`.
-- Q2: What is the bounce rate metric and how do you write it in SQL?
--     A: Percentage of sessions with exactly 1 page view: `SUM(CASE WHEN pages_viewed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)`.
-- Q3: How do you identify entry and exit pages for each user session?
--     A: Use `FIRST_VALUE(page_name) OVER (PARTITION BY session_id ORDER BY event_time)` for entry page, and `LAST_VALUE(page_name)` with frame `ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING` for exit page.
-- Q4: How do you calculate conversion drop-off percentages between funnel steps?
--     A: `100.0 * (current_step_users - next_step_users) / current_step_users`.
-- Q5: What is the computational complexity of window-based sessionization in SQL?
--     A: O(N log N) per user partition due to sorting on `event_time`.
