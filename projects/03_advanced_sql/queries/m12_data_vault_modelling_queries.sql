-- =============================================================================
-- Module 12: Data Vault 2.0 Query Patterns — Hubs, Links, and Satellites
-- =============================================================================
-- File        : m12_data_vault_modelling_queries.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | SQLite 3.38+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Data Vault 2.0 is an enterprise data warehouse modeling methodology designed for extreme scalability, auditability, and parallel load performance.
--
-- Core Components:
--   1. Hubs       : Store unique Business Keys (e.g., hash of customer_id, load timestamp, record source).
--   2. Links      : Store many-to-many relationships/transactions between Hubs (hash keys of participating Hubs).
--   3. Satellites : Store descriptive context and temporal state attributes attached to Hubs or Links.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Enterprise Data Warehouses : Multi-source CRM / ERP data integration without schema refactoring
-- • Financial Audit Systems    : Immutable history tracking of source lineage (`record_source`, `load_date`)
-- • High-Frequency ETL Pipelines: 100% parallel ingestion of raw feeds directly into raw Data Vault tables

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

-- Hub: Customer Business Key
CREATE TABLE IF NOT EXISTS hub_customer (
    hk_customer_id TEXT PRIMARY KEY, -- Hash key (MD5 / SHA256 of business key)
    customer_id    INTEGER NOT NULL,
    load_date      TEXT NOT NULL,
    record_source  TEXT NOT NULL
);

-- Hub: Store Business Key
CREATE TABLE IF NOT EXISTS hub_store (
    hk_store_id   TEXT PRIMARY KEY,
    store_id      INTEGER NOT NULL,
    load_date     TEXT NOT NULL,
    record_source TEXT NOT NULL
);

-- Link: Customer Store Visit Relationship
CREATE TABLE IF NOT EXISTS link_customer_store (
    hk_link_cust_store TEXT PRIMARY KEY,
    hk_customer_id     TEXT NOT NULL REFERENCES hub_customer(hk_customer_id),
    hk_store_id        TEXT NOT NULL REFERENCES hub_store(hk_store_id),
    load_date          TEXT NOT NULL,
    record_source      TEXT NOT NULL
);

-- Satellite: Customer Profile Attributes (Temporal Context)
CREATE TABLE IF NOT EXISTS sat_customer_profile (
    hk_customer_id TEXT NOT NULL REFERENCES hub_customer(hk_customer_id),
    load_date      TEXT NOT NULL,
    customer_name  TEXT NOT NULL,
    email          TEXT NOT NULL,
    address        TEXT NOT NULL,
    hash_diff      TEXT NOT NULL, -- MD5 of profile attributes to detect changes
    record_source  TEXT NOT NULL,
    PRIMARY KEY (hk_customer_id, load_date)
);

-- Seed Data
INSERT INTO hub_customer (hk_customer_id, customer_id, load_date, record_source)
VALUES
    ('HK_CUST_1001', 1001, '2024-01-01 00:00:00', 'CRM_POSTGRES'),
    ('HK_CUST_1002', 1002, '2024-01-01 00:00:00', 'CRM_POSTGRES')
ON CONFLICT DO NOTHING;

INSERT INTO hub_store (hk_store_id, store_id, load_date, record_source)
VALUES
    ('HK_STORE_50', 50, '2024-01-01 00:00:00', 'POS_SYSTEM')
ON CONFLICT DO NOTHING;

INSERT INTO link_customer_store (hk_link_cust_store, hk_customer_id, hk_store_id, load_date, record_source)
VALUES
    ('HK_LINK_1001_50', 'HK_CUST_1001', 'HK_STORE_50', '2024-01-02 10:00:00', 'POS_SYSTEM')
ON CONFLICT DO NOTHING;

-- Historical Satellite records for Customer 1001 (Profile update on Jan 15)
INSERT INTO sat_customer_profile (hk_customer_id, load_date, customer_name, email, address, hash_diff, record_source)
VALUES
    ('HK_CUST_1001', '2024-01-01 00:00:00', 'Alice Johnson', 'alice@old.com', '123 Main St', 'HASH_V1', 'CRM_POSTGRES'),
    ('HK_CUST_1001', '2024-01-15 12:00:00', 'Alice Johnson', 'alice@new.com', '456 Oak Ave', 'HASH_V2', 'CRM_POSTGRES')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- QUERY 1: Extract Latest Customer State (Point-in-Time Current Snapshot View)
-- =============================================================================

WITH latest_sat AS (
    SELECT
        hk_customer_id,
        customer_name,
        email,
        address,
        load_date,
        ROW_NUMBER() OVER (
            PARTITION BY hk_customer_id
            ORDER BY load_date DESC
        ) AS rn
    FROM sat_customer_profile
)
SELECT
    h.customer_id,
    s.customer_name,
    s.email,
    s.address,
    s.load_date AS profile_updated_at,
    h.record_source
FROM hub_customer h
JOIN latest_sat s
    ON h.hk_customer_id = s.hk_customer_id
   AND s.rn = 1
ORDER BY h.customer_id;

-- Expected Output:
-- customer_id | customer_name | email         | address     | profile_updated_at
-- 1001        | Alice Johnson | alice@new.com | 456 Oak Ave | 2024-01-15 12:00:00

-- =============================================================================
-- QUERY 2: Reconstruct Information Mart (Dimensional Star Schema View from Vault)
-- =============================================================================

SELECT
    h_c.customer_id,
    s_c.customer_name,
    s_c.email,
    h_s.store_id,
    l.load_date AS store_visit_timestamp
FROM link_customer_store l
JOIN hub_customer h_c ON l.hk_customer_id = h_c.hk_customer_id
JOIN hub_store h_s    ON l.hk_store_id = h_s.hk_store_id
JOIN sat_customer_profile s_c
    ON h_c.hk_customer_id = s_c.hk_customer_id
   AND s_c.load_date = (
       SELECT MAX(sub.load_date)
       FROM sat_customer_profile sub
       WHERE sub.hk_customer_id = s_c.hk_customer_id
         AND sub.load_date <= l.load_date
   );

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. All Hub, Link, and Satellite join keys are fixed-length MD5 or SHA256 string hashes (or BINARY16/32 bytes) for ultra-fast joins.
-- 2. Point-in-Time (PIT) tables and Bridge tables are created in Data Vault to pre-calculate `ROW_NUMBER() = 1` snapshot keys for reporting layer acceleration.

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Use `hash_diff` (MD5 of concatenated payload columns) to perform zero-IO comparison during delta ingestion before inserting satellite records.
-- TIP 2: Always store `record_source` in every vault table for end-to-end lineage auditing.
-- TIP 3: Build automated PIT (Point-in-Time) tables nightly to remove window function overhead from user-facing BI queries.

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Putting foreign keys directly in Hub tables (Hubs should ONLY contain business keys; Link tables hold relationships).
-- MISTAKE 2: Updating Satellite records in-place (Satellites are insert-only append logs!).
-- MISTAKE 3: Exposing raw Data Vault structures directly to BI end users rather than creating simplified Star Schema Information Mart views.

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What are the three core table types in Data Vault 2.0 and their respective responsibilities?
--     A: Hubs (Business Keys), Links (Relationships/Transactions between Hubs), Satellites (Descriptive context and temporal state attributes).
-- Q2: Why are Hash Keys (e.g. SHA-256) used in Data Vault 2.0 instead of sequence numbers?
--     A: Hash keys can be generated independently and concurrently across distributed ingestion workers without needing global locks or sequence coordination.
-- Q3: How do you handle change detection when loading Satellite tables?
--     A: Compare the incoming payload's `hash_diff` (hash of attributes) against the latest existing satellite record's `hash_diff`. Insert only if hashes differ.
-- Q4: What is a Point-In-Time (PIT) table in Data Vault modeling?
--     A: A specialized performance optimization table that stores pre-joined surrogate keys and load dates linking Hubs to their active Satellites for specified timestamp snapshots.
-- Q5: Is Data Vault an ETL destination for direct BI reporting?
--     A: No, Data Vault serves as the enterprise raw storage vault. Information Marts (Views or Star Schema tables) are built on top of Data Vault for BI consumption.
