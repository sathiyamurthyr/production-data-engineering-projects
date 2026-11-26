/*
================================================================================
MODULE 47: Slowly Changing Dimensions (SCD Type 1, Type 2, Type 3)
================================================================================
1. EXPLANATION:
- SCD Type 1: Overwrite old values.
- SCD Type 2: Track history by inserting new row with effective start/end dates.
- SCD Type 3: Add previous_value column.
*/

SELECT 
    customer_id,
    first_name,
    city,
    effective_start_date,
    effective_end_date,
    is_current
FROM dim_customers
ORDER BY customer_id, effective_start_date;
