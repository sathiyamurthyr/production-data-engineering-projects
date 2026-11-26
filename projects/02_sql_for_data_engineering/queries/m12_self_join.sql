/*
================================================================================
MODULE 12: Self Join & Hierarchical Queries
================================================================================
1. EXPLANATION:
Self Join joins a table to itself to resolve parent-child or employee-manager relationships.
*/

SELECT 
    e.employee_id,
    e.first_name || ' ' || e.last_name AS employee_name,
    m.first_name || ' ' || m.last_name AS manager_name
FROM dim_employees AS e
LEFT JOIN dim_employees AS m ON e.manager_id = m.employee_id;
