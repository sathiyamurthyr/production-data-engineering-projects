/*
================================================================================
MODULE 35: Database Transactions (BEGIN, COMMIT, ROLLBACK)
================================================================================
1. EXPLANATION:
Transactions bundle multiple SQL operations into an all-or-nothing execution unit.
*/

BEGIN TRANSACTION;
UPDATE dim_customers SET city = 'San Jose' WHERE customer_id = 'CUST002';
COMMIT;

SELECT customer_id, city FROM dim_customers WHERE customer_id = 'CUST002';
