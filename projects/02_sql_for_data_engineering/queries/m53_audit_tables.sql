/*
================================================================================
MODULE 53: Pipeline Audit Logging Tables
================================================================================
1. EXPLANATION:
Audit log tables record pipeline job execution start/end times, row counts, and status errors.
*/

SELECT 
    log_id,
    pipeline_name,
    table_name,
    records_inserted,
    status,
    executed_at
FROM audit_logs
ORDER BY log_id DESC;
