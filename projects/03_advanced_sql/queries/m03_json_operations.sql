-- =============================================================================
-- Module 03: JSON Operations — Parsing and Extracting Semi-Structured Data
-- =============================================================================
-- File        : m03_json_operations.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | Snowflake (VARIANT) | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- Modern data pipelines ingest JSON from APIs, event streams, and NoSQL systems.
-- PostgreSQL provides two JSON types:
--   json  : Stored as text, validated, no indexing support
--   jsonb : Binary format, supports GIN indexes, faster for querying
--
-- Key operators:
--   ->   : Get JSON field by key (returns JSON type)
--   ->>  : Get JSON field by key (returns TEXT)
--   #>   : Get by path array (returns JSON)
--   #>>  : Get by path array (returns TEXT)
--   jsonb_array_elements() : Expand JSON array to rows
--   jsonb_each()           : Expand JSON object to key-value rows

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- • Parsing webhook payloads from Stripe, GitHub, Shopify stored as JSON
-- • Extracting user behavior events from analytics event streams
-- • Querying product catalogs with variable attributes stored in JSONB
-- • Transforming API response JSON into relational rows for downstream loading

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS api_events (
    event_id    SERIAL    PRIMARY KEY,
    event_type  TEXT      NOT NULL,
    source      TEXT      NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),
    payload     JSONB     NOT NULL   -- JSONB for indexed querying
);

INSERT INTO api_events (event_type, source, received_at, payload)
VALUES
    (
        'order.created',
        'shopify',
        '2024-01-15 10:30:00',
        '{
            "order_id": "ORD-001",
            "customer": {
                "id": 1001,
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "tier": "premium"
            },
            "items": [
                {"sku": "LAPTOP-X1", "qty": 1, "price": 1299.99, "category": "Electronics"},
                {"sku": "CASE-001",   "qty": 2, "price":   29.99, "category": "Accessories"}
            ],
            "total": 1359.97,
            "currency": "USD",
            "shipping": {"method": "express", "days": 2},
            "tags": ["vip", "repeat_customer"],
            "metadata": {"campaign_id": "SUMMER24", "referrer": "email"}
        }'::JSONB
    ),
    (
        'order.created',
        'shopify',
        '2024-01-15 11:00:00',
        '{
            "order_id": "ORD-002",
            "customer": {
                "id": 1002,
                "name": "Bob Smith",
                "email": "bob@example.com",
                "tier": "standard"
            },
            "items": [
                {"sku": "PHONE-S22", "qty": 1, "price": 899.00, "category": "Electronics"}
            ],
            "total": 899.00,
            "currency": "USD",
            "shipping": {"method": "standard", "days": 5},
            "tags": ["new_customer"],
            "metadata": {"campaign_id": null, "referrer": "google"}
        }'::JSONB
    ),
    (
        'user.signup',
        'webapp',
        '2024-01-15 12:00:00',
        '{
            "user_id": 2001,
            "email": "carol@example.com",
            "profile": {
                "first_name": "Carol",
                "last_name": "Davis",
                "country": "US",
                "preferences": {
                    "newsletter": true,
                    "sms": false,
                    "notifications": ["email", "push"]
                }
            },
            "utm": {"source": "instagram", "medium": "social", "campaign": "BRAND_AWARENESS"}
        }'::JSONB
    )
ON CONFLICT DO NOTHING;

-- =============================================================================
-- QUERY 1: Basic JSON Field Extraction
-- =============================================================================

SELECT
    event_id,
    event_type,
    source,
    received_at,

    -- ->> returns TEXT from the top-level key
    payload ->> 'order_id'                          AS order_id,

    -- Navigate nested objects with chained -> then ->>
    payload -> 'customer' ->> 'name'                AS customer_name,
    payload -> 'customer' ->> 'email'               AS customer_email,
    payload -> 'customer' ->> 'tier'                AS customer_tier,

    -- Numeric values: cast after extraction
    (payload ->> 'total')::NUMERIC                  AS order_total,
    payload ->> 'currency'                          AS currency,

    -- Nested object field
    payload -> 'shipping' ->> 'method'              AS shipping_method,
    (payload -> 'shipping' ->> 'days')::INT         AS shipping_days

FROM api_events
WHERE event_type = 'order.created';

-- =============================================================================
-- QUERY 2: Path-based Extraction with #>> Operator
-- =============================================================================
-- #>> extracts by a path array, useful for deeply nested fields

SELECT
    event_id,
    payload #>> '{customer, id}'                    AS customer_id,
    payload #>> '{customer, name}'                  AS customer_name,
    payload #>> '{metadata, campaign_id}'           AS campaign_id,
    payload #>> '{metadata, referrer}'              AS referrer,
    payload #>> '{shipping, method}'                AS ship_method
FROM api_events
WHERE event_type = 'order.created';

-- =============================================================================
-- QUERY 3: Expanding JSON Arrays — jsonb_array_elements()
-- =============================================================================
-- Explodes the "items" array so each line item becomes its own row

SELECT
    e.event_id,
    e.payload ->> 'order_id'                        AS order_id,
    e.payload -> 'customer' ->> 'name'              AS customer_name,

    -- Expand the "items" array into individual rows
    item ->> 'sku'                                  AS sku,
    (item ->> 'qty')::INT                           AS quantity,
    (item ->> 'price')::NUMERIC                     AS unit_price,
    item ->> 'category'                             AS category,

    -- Calculated fields
    (item ->> 'qty')::INT * (item ->> 'price')::NUMERIC AS line_total

FROM api_events e,
     -- LATERAL is implicit with set-returning functions in FROM clause
     jsonb_array_elements(e.payload -> 'items') AS item

WHERE e.event_type = 'order.created'
ORDER BY e.event_id, sku;

-- Expected Output:
-- event_id | order_id | customer_name  | sku       | quantity | unit_price | line_total
-- 1        | ORD-001  | Alice Johnson  | CASE-001  | 2        | 29.99      | 59.98
-- 1        | ORD-001  | Alice Johnson  | LAPTOP-X1 | 1        | 1299.99    | 1299.99
-- 2        | ORD-002  | Bob Smith      | PHONE-S22 | 1        | 899.00     | 899.00

-- =============================================================================
-- QUERY 4: Expanding JSON Arrays with Indexes
-- =============================================================================
-- jsonb_array_elements_text() for TEXT arrays
-- jsonb_array_elements() WITH ORDINALITY for positional index

SELECT
    event_id,
    payload ->> 'order_id'                          AS order_id,
    tag                                             AS customer_tag,
    tag_position

FROM api_events,
     jsonb_array_elements_text(payload -> 'tags')
         WITH ORDINALITY AS t(tag, tag_position)

WHERE event_type = 'order.created'
ORDER BY event_id, tag_position;

-- =============================================================================
-- QUERY 5: Querying Nested Objects with jsonb_each()
-- =============================================================================
-- Turns JSON object keys into rows — useful for EAV-style JSON attributes

SELECT
    event_id,
    payload ->> 'order_id'                          AS order_id,
    kv.key                                          AS metadata_key,
    kv.value                                        AS metadata_value
FROM api_events,
     jsonb_each(payload -> 'metadata') AS kv
WHERE event_type = 'order.created'
ORDER BY event_id, kv.key;

-- =============================================================================
-- QUERY 6: JSON Containment and Existence Operators
-- =============================================================================
-- @> : Does left JSON contain right JSON? (containment)
-- ?  : Does key exist at top level?
-- ?| : Does any of these keys exist?
-- ?& : Do all of these keys exist?

-- Find orders tagged as VIP
SELECT event_id, payload ->> 'order_id' AS order_id
FROM api_events
WHERE payload -> 'tags' @> '["vip"]'::JSONB;

-- Find events where 'metadata' key exists
SELECT event_id, event_type
FROM api_events
WHERE payload ? 'metadata';

-- Find events where EITHER 'shipping' OR 'utm' key exists
SELECT event_id, event_type
FROM api_events
WHERE payload ?| ARRAY['shipping', 'utm'];

-- Find events where BOTH 'customer' AND 'items' keys exist
SELECT event_id, event_type
FROM api_events
WHERE payload ?& ARRAY['customer', 'items'];

-- =============================================================================
-- QUERY 7: GIN Index on JSONB for High-Performance JSON Queries
-- =============================================================================

-- Create GIN index on the payload column for fast @>, ?, ?| queries
CREATE INDEX IF NOT EXISTS idx_api_events_payload_gin
    ON api_events USING GIN (payload);

-- Create a targeted functional index on a frequently-queried nested field
CREATE INDEX IF NOT EXISTS idx_api_events_customer_tier
    ON api_events ((payload -> 'customer' ->> 'tier'));

-- Create index on event_type + a JSON extraction for compound queries
CREATE INDEX IF NOT EXISTS idx_api_events_type_source
    ON api_events (event_type, source, received_at DESC);

-- =============================================================================
-- QUERY 8: JSON Aggregation — Building JSON from Relational Data
-- =============================================================================
-- Reconstruct a JSON structure from normalized order tables

WITH order_line_items AS (
    SELECT
        e.event_id,
        e.payload ->> 'order_id'                AS order_id,
        jsonb_build_object(
            'sku',       item ->> 'sku',
            'qty',       (item ->> 'qty')::INT,
            'price',     (item ->> 'price')::NUMERIC,
            'line_total', (item->>'qty')::INT * (item->>'price')::NUMERIC
        )                                        AS item_json
    FROM api_events e,
         jsonb_array_elements(e.payload -> 'items') AS item
    WHERE e.event_type = 'order.created'
)

SELECT
    order_id,
    COUNT(*)                                     AS item_count,
    SUM((item_json ->> 'line_total')::NUMERIC)   AS order_total,
    -- Aggregate all items back into a JSON array
    jsonb_agg(item_json ORDER BY item_json ->> 'sku') AS items_summary
FROM order_line_items
GROUP BY order_id;

-- =============================================================================
-- QUERY 9: Snowflake-Style JSON Queries (for reference)
-- =============================================================================

/*
-- In Snowflake, JSON is stored in VARIANT columns:
-- CREATE TABLE api_events (payload VARIANT);

-- Snowflake path syntax uses colon notation:
SELECT
    payload:order_id::STRING            AS order_id,
    payload:customer.name::STRING       AS customer_name,
    payload:customer.email::STRING      AS customer_email,
    payload:total::FLOAT                AS order_total
FROM api_events;

-- Snowflake FLATTEN to expand arrays:
SELECT
    e.payload:order_id::STRING          AS order_id,
    f.value:sku::STRING                 AS sku,
    f.value:price::FLOAT                AS price
FROM api_events e,
     LATERAL FLATTEN(input => e.payload:items) f;
*/

-- =============================================================================
-- QUERY 10: Production JSON ETL Pattern — Staging to Relational
-- =============================================================================
-- Full ETL from raw JSON events into a normalized orders table

CREATE TABLE IF NOT EXISTS orders_clean (
    order_id        TEXT          PRIMARY KEY,
    customer_id     INT,
    customer_name   TEXT,
    customer_email  TEXT,
    customer_tier   TEXT,
    order_total     NUMERIC(12,2),
    currency        TEXT,
    shipping_method TEXT,
    shipping_days   INT,
    campaign_id     TEXT,
    referrer        TEXT,
    tags            TEXT[],
    source          TEXT,
    received_at     TIMESTAMP
);

-- Upsert pattern: process new events, skip already-processed ones
INSERT INTO orders_clean (
    order_id, customer_id, customer_name, customer_email, customer_tier,
    order_total, currency, shipping_method, shipping_days,
    campaign_id, referrer, tags, source, received_at
)
SELECT
    payload ->> 'order_id',
    (payload -> 'customer' ->> 'id')::INT,
    payload -> 'customer' ->> 'name',
    payload -> 'customer' ->> 'email',
    payload -> 'customer' ->> 'tier',
    (payload ->> 'total')::NUMERIC,
    payload ->> 'currency',
    payload -> 'shipping' ->> 'method',
    (payload -> 'shipping' ->> 'days')::INT,
    payload #>> '{metadata, campaign_id}',
    payload #>> '{metadata, referrer}',
    -- Convert JSON array to PostgreSQL TEXT array
    ARRAY(SELECT jsonb_array_elements_text(payload -> 'tags')),
    source,
    received_at
FROM api_events
WHERE event_type = 'order.created'
ON CONFLICT (order_id) DO UPDATE SET
    customer_tier   = EXCLUDED.customer_tier,
    order_total     = EXCLUDED.order_total,
    campaign_id     = EXCLUDED.campaign_id;

-- Verify
SELECT * FROM orders_clean ORDER BY received_at;

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. JSONB is faster than JSON for querying — always prefer jsonb for new designs
-- 2. GIN index enables fast containment (@>) and key existence (?) queries
--    but adds ~20-30% storage overhead; use only on frequently queried columns
-- 3. jsonb_array_elements() produces one row per element — joins can explode rows
--    Use COUNT in intermediate CTEs before joining to prevent row explosion
-- 4. Casting (payload->>'total')::NUMERIC prevents implicit type errors
-- 5. Avoid jsonb_each on every row at scale — extract to relational columns first

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Using -> when you need text (->) returns JSON, ->> returns TEXT
-- MISTAKE 2: Forgetting ::cast after ->> extraction before numeric operations
-- MISTAKE 3: Not indexing JSONB columns — full scans on JSON are very slow
-- MISTAKE 4: NULL JSON values: payload->>'missing_key' returns NULL, not error
-- MISTAKE 5: Using json (not jsonb) type — cannot be indexed

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the difference between json and jsonb in PostgreSQL?
--     A: json stores raw text (preserves whitespace, key order). jsonb stores
--        parsed binary (faster queries, supports GIN indexes, no duplicate keys,
--        no preserved key order). Always use jsonb for queryable data.

-- Q2: How would you handle a JSON field containing an array of objects in SQL?
--     A: Use jsonb_array_elements() to LATERAL join the array, producing one row
--        per element. Then extract fields from each element using ->> or #>> operators.

-- Q3: How do you efficiently query for a specific value inside a JSON array?
--     A: Use the containment operator @>:
--        WHERE payload->'tags' @> '["vip"]'::JSONB
--        This uses the GIN index for fast lookup.

-- Q4: What is the performance trade-off of storing data as JSON vs. relational columns?
--     A: JSON is flexible (schema-on-read) but slower for filtered queries and
--        aggregations. Relational columns support B-tree indexes, statistics, and
--        query planner optimizations. Best practice: extract hot query fields
--        into relational columns; keep raw JSON for audit/reprocessing.

-- Q5: How would you migrate from JSON columns to a fully normalized schema?
--     A: 1) Create new relational tables. 2) ETL existing JSON rows into columns
--        using jsonb_populate_record or manual extraction. 3) Add NOT NULL constraints
--        as data quality improves. 4) Keep JSON column for backward compatibility
--        during transition period.
