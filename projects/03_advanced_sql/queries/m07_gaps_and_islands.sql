-- =============================================================================
-- Module 07: Gaps and Islands Problem Patterns
-- =============================================================================
-- File        : m07_gaps_and_islands.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- The "Gaps and Islands" problem is a classic advanced SQL challenge:
--   • Islands : Contiguous ranges of rows meeting a specific condition (e.g. consecutive daily logins).
--   • Gaps    : Missing values or ranges within a sequence (e.g. missing invoice numbers, inactive periods).
--
-- Primary Solution Techniques:
--   1. Row Number Difference Technique: `date_col - ROW_NUMBER() OVER (ORDER BY date_col)` produces a constant value for consecutive dates.
--   2. LAG / Conditionally Accumulated Sum: Flag state changes using LAG, then SUM(flag) OVER () to assign unique Island IDs.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • User Engagement     : Calculating active streak days (e.g. Duolingo or GitHub commit streaks)
-- • Audit & Compliance  : Identifying missing sequential invoice numbers or transaction IDs (Gaps)
-- • Infrastructure Monitoring: Server uptime / downtime continuous block analysis
-- • Telematics          : Vehicle trajectory sessionization based on engine signal gaps

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_logins (
    login_id    INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    login_date  TEXT NOT NULL
);

INSERT INTO user_logins (login_id, user_id, login_date)
VALUES
    -- User 101: Streak 1 (Jan 1-3), Gap (Jan 4-5), Streak 2 (Jan 6-8)
    (1,  101, '2024-01-01'),
    (2,  101, '2024-01-02'),
    (3,  101, '2024-01-03'),
    (4,  101, '2024-01-06'),
    (5,  101, '2024-01-07'),
    (6,  101, '2024-01-08'),
    -- User 102: Streak 1 (Jan 1-2), Gap, Single login (Jan 5)
    (7,  102, '2024-01-01'),
    (8,  102, '2024-01-02'),
    (9,  102, '2024-01-05')
ON CONFLICT(login_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS invoice_sequence (
    seq_id    INTEGER PRIMARY KEY,
    status    TEXT NOT NULL
);

INSERT INTO invoice_sequence (seq_id, status)
VALUES
    (1001, 'ISSUED'),
    (1002, 'ISSUED'),
    (1003, 'ISSUED'),
    (1006, 'ISSUED'), -- Gap 1004-1005
    (1007, 'ISSUED'),
    (1010, 'ISSUED')  -- Gap 1008-1009
ON CONFLICT(seq_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: Islands — Finding Consecutive Login Streaks per User
-- =============================================================================
-- Method: Row Number Difference Technique

WITH ranked_logins AS (
    SELECT
        user_id,
        login_date,
        -- Convert date to julian day / integer offset, or subtract row_number
        -- In SQLite/Postgres, we can subtract ROW_NUMBER() days from login_date
        -- Using julianday for portable SQLite date arithmetic
        CAST(JULIANDAY(login_date) - ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY login_date
        ) AS INTEGER) AS island_group_id
    FROM user_logins
)
SELECT
    user_id,
    MIN(login_date) AS streak_start_date,
    MAX(login_date) AS streak_end_date,
    COUNT(*)        AS streak_length_days
FROM ranked_logins
GROUP BY user_id, island_group_id
ORDER BY user_id, streak_start_date;

-- Expected Output:
-- user_id | streak_start_date | streak_end_date | streak_length_days
-- 101     | 2024-01-01        | 2024-01-03      | 3
-- 101     | 2024-01-06        | 2024-01-08      | 3
-- 102     | 2024-01-01        | 2024-01-02      | 2
-- 102     | 2024-01-05        | 2024-01-05      | 1

-- =============================================================================
-- QUERY 2: Gaps — Finding Missing Invoice Sequence Numbers
-- =============================================================================

WITH seq_with_next AS (
    SELECT
        seq_id AS current_seq,
        LEAD(seq_id) OVER (ORDER BY seq_id) AS next_seq
    FROM invoice_sequence
)
SELECT
    current_seq + 1 AS gap_start_id,
    next_seq - 1    AS gap_end_id,
    (next_seq - current_seq - 1) AS missing_count
FROM seq_with_next
WHERE next_seq IS NOT NULL
  AND next_seq - current_seq > 1
ORDER BY gap_start_id;

-- Expected Output:
-- gap_start_id | gap_end_id | missing_count
-- 1004         | 1005       | 2
-- 1008         | 1009       | 2

-- =============================================================================
-- QUERY 3: Islands via LAG Flag & Conditional Cumulative Sum
-- =============================================================================
-- Useful when island condition is not simple date increment (e.g. status changes)

CREATE TABLE IF NOT EXISTS server_status (
    event_time TEXT PRIMARY KEY,
    server_id  INTEGER NOT NULL,
    status     TEXT NOT NULL  -- 'UP' or 'DOWN'
);

INSERT INTO server_status (event_time, server_id, status) VALUES
    ('2024-01-01 10:00:00', 1, 'UP'),
    ('2024-01-01 10:05:00', 1, 'UP'),
    ('2024-01-01 10:10:00', 1, 'DOWN'),
    ('2024-01-01 10:15:00', 1, 'DOWN'),
    ('2024-01-01 10:20:00', 1, 'UP')
ON CONFLICT DO NOTHING;

WITH status_changes AS (
    SELECT
        event_time,
        server_id,
        status,
        CASE
            WHEN LAG(status) OVER (PARTITION BY server_id ORDER BY event_time) = status THEN 0
            ELSE 1
        END AS is_new_island
    FROM server_status
),
island_groups AS (
    SELECT
        event_time,
        server_id,
        status,
        SUM(is_new_island) OVER (PARTITION BY server_id ORDER BY event_time) AS island_id
    FROM status_changes
)
SELECT
    server_id,
    status,
    MIN(event_time) AS status_start_time,
    MAX(event_time) AS status_end_time,
    COUNT(*)        AS sample_count
FROM island_groups
GROUP BY server_id, status, island_id
ORDER BY server_id, status_start_time;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. `(user_id, login_date)` index eliminates full table sort for window ranking.
-- 2. Row number difference technique requires only 1 window function pass.
-- 3. LAG + Cumulative SUM requires 2 window passes (CTE chaining).

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Ensure dates are normalized (truncated to day level) before applying row number subtraction.
-- TIP 2: Use LEAD() to find missing gaps cleanly without generating millions of numbers in a dummy spine table.
-- TIP 3: Pre-filter input rows to keep only relevant statuses before running island grouping.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Forgetting duplicate dates in input data. Deduplicate login dates per user prior to running ROW_NUMBER().
-- MISTAKE 2: Subtracting non-integer dates directly without date conversion functions in dialects like SQLite/Oracle.
-- MISTAKE 3: Using recursive CTEs for gap finding when simple LEAD() window functions are 100x faster.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the core mathematical intuition behind `date - ROW_NUMBER()` in Gaps & Islands?
--     A: If dates are strictly consecutive (1 day apart), both `date` and `ROW_NUMBER()` increase at identical rates of +1. Their difference remains constant, uniquely identifying that island.
-- Q2: How do you identify gaps in continuous primary key sequences?
--     A: Use `LEAD(id) OVER (ORDER BY id)` and filter rows where `next_id - current_id > 1`.
-- Q3: What happens if there are duplicate login entries on the same day for a user?
--     A: `ROW_NUMBER()` will increment while the date remains same, breaking the island calculation. Input must be deduplicated (`SELECT DISTINCT user_id, login_date`) first.
-- Q4: When should you use the LAG + SUM(flag) method over the ROW_NUMBER difference method?
--     A: When islands are defined by matching state values (e.g. 'UP', 'DOWN', 'ACTIVE', 'INACTIVE') rather than sequential integer increments.
-- Q5: How do you calculate the longest streak of consecutive days for each user?
--     A: Compute island lengths using Gaps & Islands, then run `MAX(streak_length) GROUP BY user_id`.
