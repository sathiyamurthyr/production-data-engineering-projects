/*
================================================================================
MODULE 01: SQL Fundamentals in Data Engineering
================================================================================

1. EXPLANATION:
SQL (Structured Query Language) is the declarative language for relational database
management systems (RDBMS) and distributed data warehouses (Snowflake, Databricks SQL, Redshift, BigQuery).

2. BUSINESS USE CASE:
Inspect database metadata tables to audit schema structures before executing ETL pipelines.

3. PRODUCTION EXAMPLE:
Query schema catalog to verify table availability.

4. EXPECTED OUTPUT:
List of table names in current database context.

5. PERFORMANCE NOTES:
Metadata catalog queries run in O(1) time against internal system indexes.

6. OPTIMIZATION TIPS:
Never query `SELECT * FROM metadata_table` without filtering specific schema names.

7. COMMON MISTAKES:
Assuming SQL syntax is identical across dialects (PostgreSQL vs Snowflake vs SQLite).

8. INTERVIEW QUESTIONS:
Q: What is the difference between DDL, DML, DCL, and TCL in SQL?
A: DDL (Data Definition: CREATE, ALTER, DROP), DML (Data Manipulation: SELECT, INSERT, UPDATE, DELETE),
   DCL (Data Control: GRANT, REVOKE), TCL (Transaction Control: COMMIT, ROLLBACK).
*/

SELECT name, type FROM sqlite_master WHERE type='table' ORDER BY name;
