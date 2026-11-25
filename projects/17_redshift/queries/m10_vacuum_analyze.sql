/*
================================================================================
MODULE 10: DATABASE MAINTENANCE (VACUUM & ANALYZE)
================================================================================
Explanation:
  Redshift relies on VACUUM and ANALYZE operations to maintain optimal performance:
  - VACUUM: Reclaims storage space from deleted rows and resorts data according
    to the sort keys. (e.g. FULL, REINDEX, SORT ONLY, DELETE ONLY).
  - ANALYZE: Updates table statistics (distributions, frequency tables) which are
    critical for the query planner to choose efficient join strategies (e.g. Hash Joins
    vs. Merge Joins).
  
  Modern Redshift clusters automatically perform vacuuming and analyzing in the
  background (Auto Vacuum / Auto Analyze), but manual interventions are still
  highly common post-bulk-ETL batches.

Business Use Case:
  Running scheduled database maintenance tasks on a transactional database to prevent
  degradation of analytical dashboard queries over time.

Production Example:
  Admin scripts tracking tables with high unsorted row percentages and outdated statistics,
  followed by maintenance instructions.

Expected Output:
  SQL command templates for vacuum and analyze tasks alongside monitoring queries.

Performance Notes:
  - A table with a high unsorted percentage (> 20%) requires Redshift to scan a larger
    amount of disk space, degrading sort key effectiveness.
  - Outdated table statistics lead the planner to make bad join decisions, such as
    attempting to broadcast a large table to all nodes.

Optimization Tips:
  - Run `VACUUM DELETE ONLY` if you perform heavy updates/deletes and don't care about
    re-sorting immediately. This is much faster than a standard `VACUUM FULL`.
  - Always run `ANALYZE` after loading data into a staging or dimension table, and before
    joining it with other tables.

Common Mistakes:
  - Running a full `VACUUM` on the entire database during peak production business hours.
    This creates high CPU/IO locking and slows down user queries.
  - Omitting `ANALYZE` after a major data refresh, causing queries to run 10x slower
    due to wrong row count estimations.

Interview Questions:
  1. What is the difference between `VACUUM FULL` and `VACUUM REINDEX`?
     Answer: `VACUUM FULL` reclaims disk space from deleted rows and resorts all rows.
     `VACUUM REINDEX` is specifically used for tables with interleaved sort keys to
     re-analyze the distribution of values and re-index the interleaved columns.
  2. How does Redshift maintain tables automatically?
     Answer: Redshift runs Auto Analyze and Auto Vacuum in the background during periods
     of low cluster activity. However, if there are heavy continuous write loads,
     manual vacuuming/analyzing is recommended as part of the ETL batch.
================================================================================
*/

-- =======================================================================
-- 1. Standard Maintenance Commands (For manual maintenance pipelines)
-- =======================================================================

-- Analyze to update statistics
ANALYZE core.fact_sales;

-- Reclaims space from deleted rows and sorts the table
VACUUM FULL core.fact_sales;

-- Only resorts the table (doesn't reclaim space from deleted rows)
VACUUM SORT ONLY core.fact_sales;

-- Only reclaims disk space (doesn't resort rows)
VACUUM DELETE ONLY core.fact_sales;

-- =======================================================================
-- 2. Monitoring Unsorted Percent and Stale Stats (svv_table_info)
-- =======================================================================
SELECT 
    schemaname,
    tablename,
    tbl_rows AS row_count,
    unsorted AS pct_unsorted,             -- Needs VACUUM if > 20%
    stats_off AS pct_stats_out_of_date,   -- Needs ANALYZE if > 10%
    size AS size_in_mb,
    vacuum_sort_benefit                  -- Projected sort benefit score
FROM svv_table_info
WHERE schemaname IN ('core', 'staging')
ORDER BY unsorted DESC;

-- =======================================================================
-- 3. Historical View of Vacuum Run Times and Benefits
-- =======================================================================
SELECT 
    query AS query_id,
    table_name,
    status,
    rows_sorted,
    blocks_freed,
    start_time,
    end_time,
    DATEDIFF('second', start_time, end_time) AS duration_seconds
FROM svv_vacuum_summary
ORDER BY end_time DESC
LIMIT 20;
