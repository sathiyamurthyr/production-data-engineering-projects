/*
================================================================================
MODULE 36: ACID Compliance in Data Warehousing
================================================================================
1. EXPLANATION:
ACID guarantees Atomicity, Consistency, Isolation, and Durability across database writes.
*/

SELECT * FROM fact_payments WHERE status = 'SUCCESS';
