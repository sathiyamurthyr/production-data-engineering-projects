-- =============================================================================
-- Module 17: Cohort Retention Analysis and Churn Metrics
-- =============================================================================
-- File        : m17_churn_retention_cohorts.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Cohort Retention Analysis groups users by their signup date (the "Cohort") and tracks their activity over subsequent time periods (Month 0, Month 1, Month 2...).
--
-- Core Analytics Concepts:
--   1. Cohort Month : The calendar month when a user registered (`DATE_TRUNC('month', signup_date)`).
--   2. Activity Month: The calendar month of subsequent transactional activity.
--   3. Month Index   : Difference in months between Activity Month and Cohort Month.
--   4. Retention Rate: `% of initial cohort users active in Month N`.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • SaaS Analytics     : Measuring 30-day and 90-day subscription retention curves
-- • Mobile Game Apps   : Evaluating Day-1, Day-7, and Day-30 user retention after new feature releases
-- • Executive Reporting: Identifying user churn trends across marketing acquisition channels

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_cohort_signups (
    user_id     INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_monthly_activity (
    activity_id   INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    activity_date TEXT NOT NULL
);

INSERT INTO user_cohort_signups (user_id, signup_date)
VALUES
    (1, '2024-01-10'),
    (2, '2024-01-15'),
    (3, '2024-01-20'),
    (4, '2024-02-05'),
    (5, '2024-02-12')
ON CONFLICT(user_id) DO NOTHING;

INSERT INTO user_monthly_activity (activity_id, user_id, activity_date)
VALUES
    -- Jan Cohort (Users 1, 2, 3) - Month 0 Activity (Jan)
    (101, 1, '2024-01-12'),
    (102, 2, '2024-01-18'),
    (103, 3, '2024-01-25'),
    -- Jan Cohort - Month 1 Activity (Feb: Users 1 & 2 active, User 3 churned)
    (104, 1, '2024-02-10'),
    (105, 2, '2024-02-14'),
    -- Jan Cohort - Month 2 Activity (Mar: User 1 active)
    (106, 1, '2024-03-05'),
    -- Feb Cohort (Users 4 & 5) - Month 0 Activity (Feb)
    (107, 4, '2024-02-08'),
    (108, 5, '2024-02-15'),
    -- Feb Cohort - Month 1 Activity (Mar: User 4 active)
    (109, 4, '2024-03-10')
ON CONFLICT(activity_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: Monthly Cohort Retention Matrix
-- =============================================================================

WITH user_cohorts AS (
    SELECT
        user_id,
        SUBSTR(signup_date, 1, 7) AS cohort_month
    FROM user_cohort_signups
),
user_activities AS (
    SELECT DISTINCT
        user_id,
        SUBSTR(activity_date, 1, 7) AS activity_month
    FROM user_monthly_activity
),
cohort_index AS (
    SELECT
        uc.user_id,
        uc.cohort_month,
        ua.activity_month,
        -- Calculate month offset (Simplistic SQLite representation)
        (CAST(SUBSTR(ua.activity_month, 1, 4) AS INTEGER) - CAST(SUBSTR(uc.cohort_month, 1, 4) AS INTEGER)) * 12 +
        (CAST(SUBSTR(ua.activity_month, 6, 2) AS INTEGER) - CAST(SUBSTR(uc.cohort_month, 6, 2) AS INTEGER)) AS month_number
    FROM user_cohorts uc
    JOIN user_activities ua ON uc.user_id = ua.user_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS initial_cohort_size
    FROM user_cohorts
    GROUP BY cohort_month
)
SELECT
    ci.cohort_month,
    cs.initial_cohort_size,
    COUNT(DISTINCT CASE WHEN ci.month_number = 0 THEN ci.user_id END) AS month_0_active,
    COUNT(DISTINCT CASE WHEN ci.month_number = 1 THEN ci.user_id END) AS month_1_active,
    COUNT(DISTINCT CASE WHEN ci.month_number = 2 THEN ci.user_id END) AS month_2_active,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN ci.month_number = 1 THEN ci.user_id END) / cs.initial_cohort_size, 2) AS month_1_retention_pct
FROM cohort_index ci
JOIN cohort_sizes cs ON ci.cohort_month = cs.cohort_month
GROUP BY ci.cohort_month, cs.initial_cohort_size
ORDER BY ci.cohort_month;

-- Expected Output:
-- cohort_month | initial_size | month_0_active | month_1_active | month_2_active | month_1_retention_pct
-- 2024-01      | 3            | 3              | 2              | 1              | 66.67
-- 2024-02      | 2            | 2              | 1              | 0              | 50.00

-- =============================================================================
-- QUERY 2: User Churn Rate Calculation
-- =============================================================================

WITH start_period_users AS (
    SELECT DISTINCT user_id
    FROM user_monthly_activity
    WHERE activity_date >= '2024-01-01' AND activity_date < '2024-02-01'
),
retained_in_next_period AS (
    SELECT DISTINCT user_id
    FROM user_monthly_activity
    WHERE activity_date >= '2024-02-01' AND activity_date < '2024-03-01'
)
SELECT
    (SELECT COUNT(*) FROM start_period_users) AS jan_active_users,
    COUNT(sp.user_id) AS feb_retained_users,
    (SELECT COUNT(*) FROM start_period_users) - COUNT(ret.user_id) AS churned_users,
    ROUND(100.0 * ((SELECT COUNT(*) FROM start_period_users) - COUNT(ret.user_id)) / (SELECT COUNT(*) FROM start_period_users), 2) AS monthly_churn_rate_pct
FROM start_period_users sp
LEFT JOIN retained_in_next_period ret ON sp.user_id = ret.user_id;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Deduplicate user activity events (`DISTINCT user_id, activity_month`) prior to joining to prevent row explosion.
-- 2. Index `(user_id, activity_date)` to accelerate month range joins.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Pre-aggregate daily events into a monthly user summary table (`fact_user_monthly_activity`) to speed up multi-year cohort queries.
-- TIP 2: Use `DATE_TRUNC('month', date)` in PostgreSQL / Snowflake for clean date math.
-- TIP 3: Store pre-calculated cohort size tables to avoid re-counting initial signup cohorts on every dashboard query.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Including users who signed up in Month 1 inside Month 0 calculations of prior cohorts.
-- MISTAKE 2: Calculating churn rates over incomplete calendar months (partial month bias).
-- MISTAKE 3: Confusing logo churn (user count) with revenue churn (MRR dollar loss).

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is Cohort Analysis and why is it superior to aggregate user growth metrics?
--     A: It tracks specific user groups over time, separating new user acquisition growth spikes from underlying long-term product retention trends.
-- Q2: How do you calculate Month N Retention Rate in SQL?
--     A: `(Count of active users in Month N who belonged to Cohort C) / (Total initial users in Cohort C) * 100`.
-- Q3: What is the relationship between Retention Rate and Churn Rate?
--     A: `Churn Rate = 100% - Retention Rate` for a given period.
-- Q4: How do you handle reactivated users in churn modeling?
--     A: Track them as a distinct "Reactivation" segment so they are not misclassified as brand-new acquisition signups.
-- Q5: What is DAU/MAU ratio and what does it measure?
--     A: Daily Active Users divided by Monthly Active Users. It measures product stickiness and user engagement frequency.
