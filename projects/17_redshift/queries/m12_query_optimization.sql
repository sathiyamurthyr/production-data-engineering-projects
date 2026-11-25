/*
================================================================================
MODULE 12: QUERY OPTIMIZATION & EXPLAIN PLAN INTERPRETATION
================================================================================
Explanation:
  Query optimization in Redshift relies heavily on understanding how the query
  planner translates SQL statements into execution plans. The `EXPLAIN` command
  reveals the sequence of operations (scans, joins, aggregations) and data movement
  steps between slices.
  
  Key Data Redistribution Operations:
  - DS_DIST_NONE: No data movement is required. Joins are colocated on matching slices. (Optimal)
  - DS_BCAST_INNER: The entire inner table is broadcast to all compute slices. (Efficient for small tables)
  - DS_DIST_INNER: The inner table is redistributed to match the outer table's distribution key.
  - DS_DIST_BOTH: Both tables are redistributed across the network on join keys. (High network overhead)

Business Use Case:
  Troubleshooting a slow monthly sales attribution query that is blocking dashboard refreshes.
  Optimizing the join strategies and table definitions to reduce database execution cost.

Production Example:
  Using EXPLAIN plans to analyze joins, diagnosing redistribution overhead, and applying optimizations.

Expected Output:
  SQL examples demonstrating optimization analysis queries and explains.

Performance Notes:
  - Joins causing DS_DIST_BOTH should be avoided. Changing table distribution keys to colocate
    them is the best fix.
  - Avoid subqueries in WHERE clauses when JOINs can express the same logic,
    as the planner can optimize joins much better.

Optimization Tips:
  - Ensure the larger table is the outer table in the join, and the smaller is the inner table.
  - Avoid using functions or calculations on join keys, as this breaks sort key and zone map scanning.
  - Keep VARCHAR columns as narrow as possible. Redshift allocates memory for VARCHAR columns based on
    their maximum defined size, not the actual string length, during execution, causing query memory starvation.

Common Mistakes:
  - Ignoring `DS_DIST_BOTH` on multi-million row joins.
  - Joining tables on mismatched data types (e.g. INT to VARCHAR), which disables sort keys and forces conversion.

Interview Questions:
  1. What does `DS_BCAST_INNER` mean in a Redshift EXPLAIN plan?
     Answer: `DS_BCAST_INNER` means the inner table of a join is copied to all compute nodes.
     This is highly efficient if the inner table is very small, as it allows each node to perform the
     join locally without redistributing the larger outer table.
  2. How do you resolve a `DS_DIST_BOTH` indicator in a query plan?
     Answer: `DS_DIST_BOTH` indicates that both tables are being redistributed across the network.
     You can resolve this by setting the distribution style of both tables to `KEY` on the joining column,
     thereby colocating the data.
================================================================================
*/

-- =======================================================================
-- 1. Analyzing an EXPLAIN Plan for Join Performance
-- =======================================================================

-- Run EXPLAIN to review the plan
EXPLAIN
SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    SUM(s.quantity * s.unit_price) AS total_spent
FROM core.fact_sales s
INNER JOIN core.dim_customer c 
    ON s.customer_id = c.customer_id -- Joined on matching DISTKEY (customer_id)
WHERE s.sale_date >= '2026-01-01'     -- Sorted filter column
GROUP BY c.customer_id, c.first_name, c.last_name;

-- =======================================================================
-- 2. Querying Query Execution Logs (STL_ALERT_EVENT_LOG)
-- =======================================================================
-- The stl_alert_event_log table records warnings about queries that have
-- performance issues, such as nested loops, scanning too many rows, or high network traffic.
SELECT 
    query AS query_id,
    slice,
    segment,
    step,
    alert_type, -- e.g., 'Nested Loop', 'Very selective filter', 'Bcast giant table'
    event_time,
    event_info
FROM stl_alert_event_log
ORDER BY event_time DESC
LIMIT 20;

-- =======================================================================
-- 3. Monitoring Disk Spill (Queries using temporary disk space)
-- =======================================================================
-- When a query requires more memory than WLM allocates, it spills to disk,
-- slowing down significantly.
SELECT 
    query AS query_id,
    step,
    rows,
    workmem,
    is_diskbased -- TRUE if query spilled to disk
FROM svl_query_report
WHERE is_diskbased = 't'
ORDER BY query DESC
LIMIT 10;
