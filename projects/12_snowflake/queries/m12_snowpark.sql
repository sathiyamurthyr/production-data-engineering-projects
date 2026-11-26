/*
================================================================================
MODULE 12: Extensibility with Snowpark Python UDFs & Stored Procedures
================================================================================

1. EXPLANATION:
Snowpark provides a native Python, Java, and Scala developer framework inside Snowflake. 
Python User-Defined Functions (UDFs) and Stored Procedures run securely inside Snowflake's 
sandboxed Anaconda environment without exporting data to external application servers.

2. BUSINESS USE CASE:
Perform complex machine learning feature transformations (text parsing, sentiment scoring, 
vectorized math) directly inside Snowflake warehouse compute.

3. PRODUCTION EXAMPLE:
Create scalar Python UDFs, Vectorized Pandas Python UDFs, and Python Stored Procedures, 
and invoke them natively via SQL.

4. EXPECTED OUTPUT:
Execution of Python code natively within SQL query engines returning computed metrics.

5. PERFORMANCE NOTES:
Vectorized Python UDFs (`@vectorized`) process batches of rows as Pandas DataFrames, drastically reducing Python IPC call overhead.

6. OPTIMIZATION TIPS:
- Import common libraries (`numpy`, `pandas`, `scikit-learn`) via `PACKAGES = (...)` clause for pre-installed Anaconda speed.
- Use Vectorized UDFs for heavy numerical data manipulation.

7. COMMON MISTAKES:
- Attempting network outbound REST calls inside standard UDFs (requires External Functions or Network Rules).

8. INTERVIEW QUESTIONS:
Q: What is the main operational difference between a UDF and a Stored Procedure in Snowpark?
A: A UDF returns a calculated value per row/batch and can be used in SELECT statements. A Stored Procedure performs administrative DDL/DML tasks, manages transactions, and returns a single status result or DataFrame.
================================================================================
*/

USE DATABASE DATA_ENG_DB;
USE SCHEMA ANALYTICS;
USE WAREHOUSE ETL_WH;

-- Step 1: Create Scalar Python UDF (Inline Python Code)
CREATE OR REPLACE FUNCTION CALCULATE_DISCOUNTED_PRICE(
    unit_price FLOAT,
    discount_pct FLOAT
)
RETURNS FLOAT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
HANDLER = 'calculate_discount'
AS $$
def calculate_discount(unit_price: float, discount_pct: float) -> float:
    if unit_price is None or discount_pct is None:
        return 0.0
    return round(unit_price * (1.0 - (discount_pct / 100.0)), 2)
$$;

-- Step 2: Test Scalar Python UDF in SQL
SELECT 
    product_id,
    unit_price,
    CALCULATE_DISCOUNTED_PRICE(unit_price, 15.0) AS price_with_15pct_discount
FROM FACT_SALES
LIMIT 5;

-- Step 3: Create Vectorized Python UDF using Pandas
CREATE OR REPLACE FUNCTION VECTORIZED_TAX_CALCULATOR(amount FLOAT)
RETURNS FLOAT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('pandas')
HANDLER = 'compute_tax'
AS $$
import pandas as pd

def compute_tax(amounts: pd.Series) -> pd.Series:
    # Vectorized 8.875% tax computation
    return (amounts * 0.08875).round(2)
$$;

-- Step 4: Create Python Stored Procedure for Automated Table Cleanup
CREATE OR REPLACE PROCEDURE PURGE_STALE_STAGING_DATA(days_old INT)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'purge_data'
AS $$
def purge_data(session, days_old: int) -> str:
    cmd = f"DELETE FROM DATA_ENG_DB.STAGING.STG_SALES WHERE transaction_timestamp < DATEADD(day, -{days_old}, CURRENT_TIMESTAMP())"
    res = session.sql(cmd).collect()
    return f"Successfully purged staging records older than {days_old} days."
$$;

-- Step 5: Execute Python Stored Procedure
CALL PURGE_STALE_STAGING_DATA(30);
