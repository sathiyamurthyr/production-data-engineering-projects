/*
================================================================================
MODULE 14: UNION & Set Deduplication
================================================================================
1. EXPLANATION:
UNION combines query results and performs implicit deduplication.
*/

SELECT email FROM dim_customers WHERE email IS NOT NULL
UNION
SELECT email FROM dim_employees WHERE email IS NOT NULL;
