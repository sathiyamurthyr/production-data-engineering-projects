"""
Unit and Integration Tests for 03 Advanced SQL for Data Engineering.
Validates execution of SQL modules and QueryExecutor methods against SQLite in-memory database.
"""

import os
import sys
import pytest

# Paths to schema DDL and seed data
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src.query_executor import QueryExecutor

DDL_PATH = os.path.join(BASE_DIR, "schemas", "schema_ddl.sql")
SEED_PATH = os.path.join(BASE_DIR, "datasets", "seed_data.sql")
QUERIES_DIR = os.path.join(BASE_DIR, "queries")


@pytest.fixture
def executor():
    """Fixture providing initialized QueryExecutor with schema and seed data."""
    exec_inst = QueryExecutor(db_path=":memory:")
    exec_inst.init_schema(DDL_PATH)
    exec_inst.load_seed_data(SEED_PATH)
    yield exec_inst
    exec_inst.close()


def test_schema_and_seed_initialization(executor):
    """Verify schema tables and initial seed data counts."""
    res = executor.execute_query("SELECT COUNT(*) AS cnt FROM employees;")
    assert res[0]["cnt"] == 12, "Employees table should contain 12 seed records."

    res_sales = executor.execute_query("SELECT COUNT(*) AS cnt FROM monthly_sales;")
    assert res_sales[0]["cnt"] == 12, "Monthly sales should contain 12 seed records."


def test_m01_recursive_cte_hierarchy(executor):
    """Test Recursive CTE Org Chart Traversal."""
    query = """
    WITH RECURSIVE org_chart AS (
        SELECT employee_id, full_name, manager_id, 0 AS depth
        FROM employees
        WHERE manager_id IS NULL

        UNION ALL

        SELECT e.employee_id, e.full_name, e.manager_id, oc.depth + 1
        FROM employees e
        JOIN org_chart oc ON e.manager_id = oc.employee_id
    )
    SELECT full_name, depth FROM org_chart ORDER BY depth, employee_id;
    """
    res = executor.execute_query(query)
    assert len(res) == 12, "Should traverse all 12 employees in hierarchy."
    assert res[0]["full_name"] == "Alice Johnson"
    assert res[0]["depth"] == 0


def test_m02_pivot_conditional_aggregation(executor):
    """Test Pivot via Conditional Aggregation."""
    query = """
    SELECT
        product,
        SUM(CASE WHEN sale_month = 1 THEN revenue ELSE 0 END) AS jan_rev,
        SUM(CASE WHEN sale_month = 2 THEN revenue ELSE 0 END) AS feb_rev,
        SUM(revenue) AS total_rev
    FROM monthly_sales
    GROUP BY product
    ORDER BY product;
    """
    res = executor.execute_query(query)
    assert len(res) == 2, "Should return aggregated pivot for 2 distinct products."
    laptop_row = [r for r in res if r["product"] == "Laptop"][0]
    assert laptop_row["jan_rev"] == 230000.0  # 150000 (North) + 80000 (South)


def test_m04_lateral_joins_top_n(executor):
    """Test Lateral Join / Top-N Orders per customer simulation."""
    query = """
    WITH top_orders AS (
        SELECT
            c.customer_id,
            c.customer_name,
            o.order_id,
            o.amount,
            ROW_NUMBER() OVER (PARTITION BY c.customer_id ORDER BY o.amount DESC) AS rn
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.status = 'completed'
    )
    SELECT customer_id, customer_name, order_id, amount
    FROM top_orders
    WHERE rn <= 2
    ORDER BY customer_id, rn;
    """
    res = executor.execute_query(query)
    assert len(res) > 0
    alice_top = [r for r in res if r["customer_id"] == 1]
    assert len(alice_top) == 2
    assert alice_top[0]["amount"] == 2500.00


def test_m05_window_frame_specs(executor):
    """Test Window Frame Specs (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)."""
    query = """
    SELECT
        metric_date,
        daily_revenue,
        ROUND(AVG(daily_revenue) OVER (
            PARTITION BY store_id
            ORDER BY metric_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2) AS moving_avg_3d
    FROM daily_metrics
    WHERE store_id = 101
    ORDER BY metric_date;
    """
    res = executor.execute_query(query)
    assert len(res) == 4
    # Day 1: 1000, Day 2: 1200 (avg=1100), Day 3: 800 (avg=(1000+1200+800)/3 = 1000)
    assert res[2]["moving_avg_3d"] == 1000.0


def test_m06_running_totals(executor):
    """Test Cumulative Running Total per Account."""
    query = """
    SELECT
        account_id,
        txn_date,
        txn_amount,
        SUM(txn_amount) OVER (
            PARTITION BY account_id
            ORDER BY txn_date, txn_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_balance
    FROM ledger_transactions
    WHERE account_id = 1001
    ORDER BY txn_date, txn_id;
    """
    res = executor.execute_query(query)
    assert len(res) == 3
    # 500, then 500 - 150 = 350, then 350 + 200 = 550
    assert res[0]["running_balance"] == 500.0
    assert res[1]["running_balance"] == 350.0
    assert res[2]["running_balance"] == 550.0


def test_m07_gaps_and_islands(executor):
    """Test Islands Consecutive Streak Grouping."""
    query = """
    WITH ranked_logins AS (
        SELECT
            user_id,
            login_date,
            CAST(JULIANDAY(login_date) - ROW_NUMBER() OVER (
                PARTITION BY user_id ORDER BY login_date
            ) AS INTEGER) AS island_id
        FROM user_logins
    )
    SELECT
        user_id,
        MIN(login_date) AS streak_start,
        MAX(login_date) AS streak_end,
        COUNT(*) AS streak_days
    FROM ranked_logins
    WHERE user_id = 101
    GROUP BY user_id, island_id
    ORDER BY streak_start;
    """
    res = executor.execute_query(query)
    assert len(res) == 2, "User 101 should have 2 distinct login streak islands."
    assert res[0]["streak_days"] == 3  # Jan 1-3
    assert res[1]["streak_days"] == 1  # Jan 6


def test_m08_time_series_gap_filling(executor):
    """Test Date Spine & Zero Filling."""
    query = """
    WITH RECURSIVE date_spine(spine_date) AS (
        SELECT '2024-01-01'
        UNION ALL
        SELECT DATE(spine_date, '+1 day')
        FROM date_spine
        WHERE spine_date < '2024-01-04'
    )
    SELECT
        ds.spine_date,
        COALESCE(pds.units_sold, 0) AS units_sold
    FROM date_spine ds
    LEFT JOIN product_daily_sales pds
        ON ds.spine_date = pds.sale_date AND pds.product_id = 501
    ORDER BY ds.spine_date;
    """
    res = executor.execute_query(query)
    assert len(res) == 4
    assert res[2]["spine_date"] == "2024-01-03"
    assert res[2]["units_sold"] == 0  # Missing date gap zero-filled


def test_m09_merge_upsert(executor):
    """Test Idempotent ON CONFLICT Upsert Pattern."""
    staging_rows = executor.execute_query("SELECT * FROM staging_customers;")
    for row in staging_rows:
        executor.execute_query("""
            INSERT INTO target_customers (customer_id, full_name, email, tier, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                email = EXCLUDED.email,
                tier = EXCLUDED.tier,
                updated_at = EXCLUDED.updated_at
            WHERE EXCLUDED.updated_at > target_customers.updated_at;
        """, (row["customer_id"], row["full_name"], row["email"], row["tier"], row["updated_at"]))

    res = executor.execute_query("SELECT * FROM target_customers WHERE customer_id = 1;")
    assert res[0]["tier"] == "GOLD", "Alice's tier should be updated to GOLD."
    assert res[0]["email"] == "alice_new@example.com"

    res_charlie = executor.execute_query("SELECT * FROM target_customers WHERE customer_id = 3;")
    assert len(res_charlie) == 1, "Charlie should be inserted as new customer."


def test_m11_scd2_invalidation_and_insert(executor):
    """Test SCD Type 2 Invalidation and New Version Insertion."""
    invalidation_sql = """
    UPDATE dim_employee_scd2
    SET valid_to = '2024-06-01 00:00:00', is_current = 0
    WHERE is_current = 1 AND employee_id = 101;

    INSERT INTO dim_employee_scd2 (employee_id, employee_name, department, salary, valid_from, valid_to, is_current)
    VALUES (101, 'Alice Smith', 'Product Tech', 110000.00, '2024-06-01 00:00:00', '9999-12-31 23:59:59', 1);
    """
    executor.execute_script(invalidation_sql)

    res = executor.execute_query("SELECT * FROM dim_employee_scd2 WHERE employee_id = 101 ORDER BY valid_from;")
    assert len(res) == 2, "Alice should have 2 historical SCD2 records."
    assert res[0]["is_current"] == 0
    assert res[1]["is_current"] == 1
    assert res[1]["department"] == "Product Tech"


def test_m16_sessionization(executor):
    """Test Clickstream Sessionization Logic."""
    query = """
    WITH time_deltas AS (
        SELECT
            event_id, user_id, event_time, page_name,
            LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_time
        FROM clickstream_events
    ),
    flags AS (
        SELECT
            event_id, user_id, event_time, page_name,
            CASE
                WHEN prev_time IS NULL THEN 1
                WHEN (JULIANDAY(event_time) - JULIANDAY(prev_time)) * 86400 > 1800 THEN 1
                ELSE 0
            END AS is_new_session
        FROM time_deltas
    )
    SELECT
        user_id,
        SUM(is_new_session) OVER (PARTITION BY user_id ORDER BY event_time) AS session_num
    FROM flags
    WHERE user_id = 101;
    """
    res = executor.execute_query(query)
    assert len(res) == 2
    assert res[0]["session_num"] == 1


def test_m18_cdc_deduplication(executor):
    """Test CDC Stream Deduplication for Latest Non-Deleted Snapshot."""
    query = """
    WITH ranked_cdc AS (
        SELECT
            order_id, customer_id, amount, status, cdc_op, cdc_timestamp,
            ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY lsn_seq DESC) AS rn
        FROM cdc_orders_stream
    )
    SELECT order_id, status
    FROM ranked_cdc
    WHERE rn = 1 AND cdc_op <> 'D';
    """
    res = executor.execute_query(query)
    assert len(res) == 1
    assert res[0]["order_id"] == 501
    assert res[0]["status"] == "SHIPPED"


def test_m20_production_etl_pipeline(executor):
    """Test Production ETL SQL Pipeline with Audit Logging."""
    etl_sql = """
    INSERT INTO etl_pipeline_audit_log (pipeline_name, start_time, status)
    VALUES ('TEST_ETL', DATETIME('now'), 'RUNNING');

    WITH clean AS (
        SELECT txn_id, customer_id, amount, txn_timestamp,
               ROW_NUMBER() OVER (PARTITION BY txn_id ORDER BY txn_timestamp DESC, raw_id DESC) AS rn
        FROM stg_raw_transactions
        WHERE customer_id IS NOT NULL AND amount > 0
    )
    INSERT INTO prod_transactions (txn_id, customer_id, amount, txn_timestamp, loaded_at)
    SELECT txn_id, customer_id, amount, txn_timestamp, DATETIME('now')
    FROM clean WHERE rn = 1
    ON CONFLICT(txn_id) DO UPDATE SET
        amount = EXCLUDED.amount,
        txn_timestamp = EXCLUDED.txn_timestamp;

    UPDATE etl_pipeline_audit_log
    SET status = 'SUCCESS', end_time = DATETIME('now'), rows_processed = (SELECT COUNT(*) FROM prod_transactions)
    WHERE pipeline_name = 'TEST_ETL' AND status = 'RUNNING';
    """
    executor.execute_script(etl_sql)

    res_prod = executor.execute_query("SELECT * FROM prod_transactions ORDER BY txn_id;")
    assert len(res_prod) == 1
    assert res_prod[0]["amount"] == 175.00  # Deduplicated to latest update

    res_audit = executor.execute_query("SELECT * FROM etl_pipeline_audit_log WHERE pipeline_name = 'TEST_ETL';")
    assert res_audit[0]["status"] == "SUCCESS"
    assert res_audit[0]["rows_processed"] == 1


def test_sql_files_execution(executor):
    """Verify that all 20 module SQL query files can be executed by QueryExecutor."""
    for i in range(1, 21):
        filename = f"m{i:02d}_"
        matching_files = [f for f in os.listdir(QUERIES_DIR) if f.startswith(filename) and f.endswith(".sql")]
        assert len(matching_files) == 1, f"Missing query file for module m{i:02d}"

        file_path = os.path.join(QUERIES_DIR, matching_files[0])
        # execute_file should run without throwing uncaught syntax errors
        results = executor.execute_file(file_path)
        assert isinstance(results, list), f"Execution of {matching_files[0]} should return a list"
