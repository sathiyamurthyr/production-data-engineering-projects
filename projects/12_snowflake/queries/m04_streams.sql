/*
================================================================================
MODULE 04: Change Data Capture (CDC) with Streams
================================================================================

1. EXPLANATION:
Snowflake Streams record Change Data Capture (CDC) delta changes (INSERTS, UPDATES, DELETES) 
made to a table. A stream stores zero data itself; it creates a change tracking offset on the source 
table's micro-partitions.

2. BUSINESS USE CASE:
Track ongoing incremental changes in staging tables (`STG_SALES`) and incrementally merge 
updates into production fact tables (`FACT_SALES`) without scanning historical data.

3. PRODUCTION EXAMPLE:
Create Standard and Append-Only Streams on `STG_SALES`, perform inserts/updates/deletes on staging, 
inspect `METADATA$ACTION` and `METADATA$ISUPDATE` columns, and consume the stream via `MERGE INTO`.

4. EXPECTED OUTPUT:
Stream offset populated with delta records, and target table synchronized upon MERGE.

5. PERFORMANCE NOTES:
Streams add zero storage cost. When consumed inside a transaction (DML statement), 
the stream offset automatically advances to the transaction timestamp.

6. OPTIMIZATION TIPS:
- Use `APPEND_ONLY = TRUE` for immutable event log / staging tables to optimize stream tracking overhead.
- Always consume streams inside transactions to guarantee exact-once processing semantics.

7. COMMON MISTAKES:
- Allowing streams to become stale (exceeding table's `DATA_RETENTION_TIME_IN_DAYS`), forcing recreate.

8. INTERVIEW QUESTIONS:
Q: What are the three metadata columns automatically added to a Snowflake Stream?
A: METADATA$ACTION ('INSERT' or 'DELETE'), METADATA$ISUPDATE (TRUE if row is part of UPDATE), METADATA$ROW_ID (unique row hash).
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA STAGING;
USE WAREHOUSE ETL_WH;

-- Step 1: Target Production Fact Table
CREATE OR REPLACE TABLE DATA_ENG_DB.ANALYTICS.FACT_SALES (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    category VARCHAR(50),
    quantity INT,
    unit_price NUMBER(10,2),
    total_amount NUMBER(10,2),
    payment_method VARCHAR(30),
    store_id VARCHAR(50),
    transaction_timestamp TIMESTAMP_NTZ,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Step 2: Create Standard Stream on Staging Table
CREATE OR REPLACE STREAM STG_SALES_STREAM 
ON TABLE STG_SALES 
SHOW_INITIAL_ROWS = FALSE;

-- Step 3: Insert Sample Delta Record into Staging Table
INSERT INTO STG_SALES (
    transaction_id, customer_id, product_id, category, quantity, unit_price, total_amount, payment_method, store_id, transaction_timestamp
) VALUES (
    'TXN99999', 'CUST001', 'PROD_ELEC_01', 'Electronics', 2, 1299.99, 2599.98, 'CREDIT_CARD', 'STORE_NY_01', CURRENT_TIMESTAMP()
);

-- Step 4: Inspect Stream CDC Delta Contents & Metadata Columns
SELECT 
    transaction_id,
    customer_id,
    total_amount,
    METADATA$ACTION,
    METADATA$ISUPDATE,
    METADATA$ROW_ID
FROM STG_SALES_STREAM;

-- Step 5: Consume Stream with Incremental MERGE INTO Target Fact Table
BEGIN TRANSACTION;

MERGE INTO DATA_ENG_DB.ANALYTICS.FACT_SALES AS target
USING STG_SALES_STREAM AS stream
ON target.transaction_id = stream.transaction_id
WHEN MATCHED AND stream.METADATA$ACTION = 'DELETE' AND stream.METADATA$ISUPDATE = FALSE THEN
    DELETE
WHEN MATCHED AND stream.METADATA$ACTION = 'INSERT' AND stream.METADATA$ISUPDATE = TRUE THEN
    UPDATE SET 
        target.quantity = stream.quantity,
        target.total_amount = stream.total_amount,
        target.updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED AND stream.METADATA$ACTION = 'INSERT' AND stream.METADATA$ISUPDATE = FALSE THEN
    INSERT (
        transaction_id, customer_id, product_id, category, quantity, unit_price, total_amount, payment_method, store_id, transaction_timestamp, created_at, updated_at
    ) VALUES (
        stream.transaction_id, stream.customer_id, stream.product_id, stream.category, stream.quantity, stream.unit_price, stream.total_amount, stream.payment_method, stream.store_id, stream.transaction_timestamp, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
    );

COMMIT;

-- Step 6: Verify Stream offset has cleared after consumption
SELECT COUNT(*) AS remaining_stream_rows FROM STG_SALES_STREAM;
