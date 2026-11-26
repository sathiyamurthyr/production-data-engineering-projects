/*
================================================================================
MODULE 24: Recursive CTEs & Graph Traversal
================================================================================
1. EXPLANATION:
Recursive CTEs iterate over hierarchical trees (org charts, bill of materials, dependency graphs).
*/

WITH RECURSIVE org_hierarchy AS (
    -- Anchor member: Top-level managers
    SELECT employee_id, first_name, manager_id, 1 AS depth
    FROM dim_employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive member: Subordinates
    SELECT e.employee_id, e.first_name, e.manager_id, h.depth + 1
    FROM dim_employees e
    INNER JOIN org_hierarchy h ON e.manager_id = h.employee_id
)
SELECT * FROM org_hierarchy;
