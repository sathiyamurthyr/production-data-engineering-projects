/*
================================================================================
MODULE 09: WORKLOAD MANAGEMENT (WLM) & CONCURRENCY
================================================================================
Explanation:
  Amazon Redshift Workload Management (WLM) is used to manage query concurrency,
  memory allocation, and routing. WLM defines queues where queries are executed,
  ensuring that short queries aren't blocked by long-running analytical queries.
  QMR (Query Monitoring Rules) can abort, hop, or log queries that violate defined
  resource limits (e.g. CPU time, scan rows).

  This module covers query templates to:
  - Check active WLM query states and queue allocations.
  - Review queue configurations and active slot utilization.
  - Audit queries aborted or changed by Query Monitoring Rules (QMR).
  - Calculate queue wait times vs. execution times.

Business Use Case:
  Monitoring warehouse performance to detect if ETL pipelines are stuck waiting for adhoc
  analysts' queries, or to find out which user ran a cartesian product query that occupied
  90% of cluster memory.

Production Example:
  Admin queries targeting STV/STL tables to optimize performance and check queue allocations.

Expected Output:
  Ready-to-use WLM auditing and performance tuning queries.

Performance Notes:
  - High queue wait times indicate the need for concurrency scaling or optimization
    of queries.
  - In Auto WLM (default), Redshift manages query concurrency and memory dynamically.
    Manual WLM allows pinning specific service classes.

Optimization Tips:
  - Assign specific user groups or query groups to dedicated queues. For instance,
    ETL queries should be run under a user group assigned to an ETL queue with
    dedicated memory and concurrency scaling disabled (to avoid cost spikes).
  - Implement strict QMR rules to abort queries that scan too much data or run for > 1 hour.

Common Mistakes:
  - Allocating too many queues in manual WLM (more than 5). This splits the cluster memory
    into tiny chunks, forcing queries to page to disk (S3/SSD temporary storage).
  - Leaving concurrency scaling off for heavy ad-hoc search queues, leading to query queues.

Interview Questions:
  1. What is the difference between Auto WLM and Manual WLM?
     Answer: Auto WLM uses machine learning to allocate cluster resources and determine
     concurrency dynamically. Manual WLM requires the administrator to manually define
     the number of queues, query concurrency limits, and memory percentage allocations.
  2. What are Query Monitoring Rules (QMR) in Redshift?
     Answer: QMR rules let you set metrics-based thresholds (like CPU time, execution time,
     or data scanned) on WLM queues. If a query exceeds a threshold, Redshift can trigger
     an action: logging it, hopping it to the next queue, or aborting the query.
================================================================================
*/

-- =======================================================================
-- 1. View Active Queries and their WLM Queue / Slot Information
-- =======================================================================
SELECT 
    w.query AS query_id,
    w.service_class AS queue_id,
    w.slot_count,
    SUBSTRING(q.querytxt, 1, 60) AS query_text,
    w.exec_start_time,
    DATEDIFF('second', w.exec_start_time, GETDATE()) AS duration_seconds,
    w.state -- 'running' or 'queued'
FROM stv_wlm_query_state w
INNER JOIN stl_query q 
    ON w.query = q.query
ORDER BY w.exec_start_time DESC;

-- =======================================================================
-- 2. Audit WLM Queue Wait Times vs Execution Times (Historical)
-- =======================================================================
SELECT 
    service_class AS queue_id,
    COUNT(*) AS total_queries,
    AVG(service_class_start_time - queue_start_time) / 1000000 AS avg_wait_seconds,
    AVG(service_class_end_time - service_class_start_time) / 1000000 AS avg_exec_seconds,
    MAX(service_class_end_time - service_class_start_time) / 1000000 AS max_exec_seconds
FROM stl_wlm_query
WHERE queue_start_time >= DATEADD('day', -7, GETDATE())
GROUP BY service_class
ORDER BY avg_wait_seconds DESC;

-- =======================================================================
-- 3. Check Queries Aborted or Hopped by Query Monitoring Rules (QMR)
-- =======================================================================
SELECT 
    qmr.query AS query_id,
    qmr.rule_name,
    qmr.action, -- 'abort', 'hop', or 'log'
    qmr.threshold_value,
    qmr.actual_value,
    SUBSTRING(q.querytxt, 1, 100) AS query_text,
    qmr.recordtime AS event_time
FROM stl_qmr_rule qmr
INNER JOIN stl_query q 
    ON qmr.query = q.query
ORDER BY qmr.recordtime DESC
LIMIT 50;

-- =======================================================================
-- 4. View Memory Allocations and Config for all Service Classes (Queues)
-- =======================================================================
SELECT 
    config.service_class AS queue_id,
    name AS queue_name,
    config.num_query_tasks AS concurrency_limit,
    config.query_window_size AS memory_percent,
    state.num_queued_queries AS current_queued,
    state.num_executing_queries AS current_executing
FROM stv_wlm_service_class_config config
INNER JOIN stv_wlm_service_class_state state 
    ON config.service_class = state.service_class
ORDER BY config.service_class;
