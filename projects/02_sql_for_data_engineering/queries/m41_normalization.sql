/*
================================================================================
MODULE 41: Relational Normalization (1NF, 2NF, 3NF)
================================================================================
1. EXPLANATION:
Normalization eliminates data redundancy by decomposing flat tables into related entities.
*/

SELECT e.first_name, e.last_name, d.department_name
FROM dim_employees e
JOIN dim_departments d ON e.department_id = d.department_id;
