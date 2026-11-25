-- =============================================================================
-- Module 09: MERGE and Upsert Patterns
-- =============================================================================
-- File        : m09_merge_upsert_patterns.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 15+ | SQLite 3.24+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- An "Upsert" (Update or Insert) operation synchronizes target tables with incremental source feeds.
-- If a matching primary key exists in target, UPDATE the existing record.
-- If no match exists, INSERT the new record.
--
-- SQL Dialect Implementations:
--   1. ANSI SQL MERGE (Snowflake, Databricks, PostgreSQL 15+, Oracle, BigQuery):
--      MERGE INTO target USING source ON target.id = source.id ...
--   2. ON CONFLICT (PostgreSQL 9.5+, SQLite 3.24+):
--      INSERT INTO target VALUES (...) ON CONFLICT (id) DO UPDATE SET ...

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Customer Data Platform (CDP) : Syncing updated customer profiles from CRM CDC streams
-- • Inventory Management         : Real-time stock quantity adjustments from warehouse events
-- • Product Catalogs             : Idempotent daily ETL sync of e-commerce SKU prices and descriptions
-- • Event Ingestion              : Deduplicating incoming API payloads based on unique event UUIDs

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

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

-- Seed Target Table
INSERT INTO target_customers (customer_id, full_name, email, tier, updated_at)
VALUES
    (1, 'Alice Johnson', 'alice@example.com', 'SILVER', '2024-01-01 10:00:00'),
    (2, 'Bob Smith',     'bob@example.com',   'BRONZE', '2024-01-01 10:00:00')
ON CONFLICT(customer_id) DO NOTHING;

-- Seed Staging Table (1 updated row for Alice, 1 new row for Charlie)
INSERT INTO staging_customers (customer_id, full_name, email, tier, updated_at)
VALUES
    (1, 'Alice Johnson', 'alice_new@example.com', 'GOLD',   '2024-01-02 12:00:00'),
    (3, 'Charlie Brown', 'charlie@example.com',   'BRONZE', '2024-01-02 12:00:00')
ON CONFLICT(customer_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: ON CONFLICT Upsert Pattern (PostgreSQL / SQLite Standard)
-- =============================================================================

INSERT INTO target_customers (customer_id, full_name, email, tier, updated_at)
SELECT customer_id, full_name, email, tier, updated_at
FROM staging_customers
ON CONFLICT(customer_id) DO UPDATE SET
    full_name  = EXCLUDED.full_name,
    email      = EXCLUDED.email,
    tier       = EXCLUDED.tier,
    updated_at = EXCLUDED.updated_at
WHERE EXCLUDED.updated_at > target_customers.updated_at;

-- Verify Target State
SELECT * FROM target_customers ORDER BY customer_id;

-- Expected Output:
-- customer_id | full_name     | email               | tier   | updated_at
-- 1           | Alice Johnson | alice_new@example.com| GOLD   | 2024-01-02 12:00:00
-- 2           | Bob Smith     | bob@example.com     | BRONZE | 2024-01-01 10:00:00
-- 3           | Charlie Brown | charlie@example.com | BRONZE | 2024-01-02 12:00:00

-- =============================================================================
-- QUERY 2: Conditional DO NOTHING on Duplicate Key
-- =============================================================================
-- Ignores incoming duplicates if primary key already exists (Idempotent Insert)

INSERT INTO target_customers (customer_id, full_name, email, tier, updated_at)
VALUES (2, 'Bob Smith Duplicate', 'bob_dup@example.com', 'PLATINUM', '2024-01-03 00:00:00')
ON CONFLICT(customer_id) DO NOTHING;

-- Verify Bob's data was NOT overwritten
SELECT * FROM target_customers WHERE customer_id = 2;

-- =============================================================================
-- QUERY 3: ANSI MERGE Statement Reference (Snowflake / Databricks / Postgres 15+)
-- =============================================================================
/*
MERGE INTO target_customers AS target
USING staging_customers AS source
    ON target.customer_id = source.customer_id

-- Match Condition 1: Update when source is newer
WHEN MATCHED AND source.updated_at > target.updated_at THEN
    UPDATE SET
        target.full_name  = source.full_name,
        target.email      = source.email,
        target.tier       = source.tier,
        target.updated_at = source.updated_at

-- Match Condition 2: Optional Soft Delete
WHEN MATCHED AND source.tier = 'DELETED' THEN
    DELETE

-- Not Matched Condition: Insert new records
WHEN NOT MATCHED THEN
    INSERT (customer_id, full_name, email, tier, updated_at)
    VALUES (source.customer_id, source.full_name, source.email, source.tier, source.updated_at);
*/

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Matching keys in MERGE / ON CONFLICT must be indexed (Primary Key / Unique Index) on the target table.
-- 2. Deduplicate staging source tables prior to running MERGE to avoid "MERGE ON target row matched multiple source rows" errors.
-- 3. In cloud data warehouses (Snowflake / Delta Lake), MERGE operates at partition level; structure join keys to match target clustering keys.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Always include a timestamp inequality check (`EXCLUDED.updated_at > target.updated_at`) to prevent out-of-order CDC updates from corrupting state.
-- TIP 2: In PostgreSQL/SQLite, `EXCLUDED` pseudo-table represents the row proposed for insertion.
-- TIP 3: Pre-aggregate or deduplicate staging tables (`ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1`).

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Running MERGE when staging contains multiple records with the same Primary Key (fails with non-deterministic merge error).
-- MISTAKE 2: Overwriting target fields unconditionally without checking if incoming CDC record is newer.
-- MISTAKE 3: Forgetting to lock target table or wrap in transaction when performing batch upsert operations.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What happens if a MERGE statement matches multiple source rows to a single target row?
--     A: SQL engine throws a runtime error ("ON search condition matched multiple rows") to prevent non-deterministic updates.
-- Q2: What is the `EXCLUDED` keyword in PostgreSQL / SQLite `ON CONFLICT`?
--     A: It is a special pseudo-table referencing the tuple/row attempted to be inserted by the INSERT statement.
-- Q3: How do you handle out-of-order CDC data in an Upsert query?
--     A: Compare event timestamps: only UPDATE when `EXCLUDED.event_timestamp > target.event_timestamp`.
-- Q4: What is the difference between `ON CONFLICT DO NOTHING` and `ON CONFLICT DO UPDATE`?
--     A: `DO NOTHING` silently ignores primary key duplicates; `DO UPDATE` modifies specified target columns upon key collision.
-- Q5: Is MERGE atomic in relational databases?
--     A: Yes, MERGE runs inside a transaction boundary ensuring all matched/unmatched actions commit or rollback together.
