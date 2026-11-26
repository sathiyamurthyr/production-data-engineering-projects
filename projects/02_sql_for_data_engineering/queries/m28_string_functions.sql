/*
================================================================================
MODULE 28: String Functions (UPPER, LOWER, SUBSTR, LENGTH, TRIM)
================================================================================
1. EXPLANATION:
String functions clean and format text fields during ETL ingestion.
*/

SELECT 
    customer_id,
    UPPER(first_name) AS first_name_upper,
    LOWER(email) AS email_clean,
    LENGTH(first_name) AS name_len,
    SUBSTR(customer_id, 1, 4) AS id_prefix
FROM dim_customers;
