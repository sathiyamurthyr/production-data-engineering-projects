/*
================================================================================
MODULE 20: COALESCE & Fallback Value Replacement
================================================================================
1. EXPLANATION:
COALESCE returns the first non-NULL argument in a list. Critical for imputing missing values.
*/

SELECT 
    employee_id,
    first_name,
    COALESCE(email, 'no_email@company.com') AS contact_email
FROM dim_employees;
