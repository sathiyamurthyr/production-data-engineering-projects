-- =============================================================================
-- Module 01: Recursive CTE for Hierarchical Data (Org Chart Traversal)
-- =============================================================================
-- File        : m01_recursive_cte_hierarchy.sql
-- Project     : 03 Advanced SQL for Data Engineering
-- Author      : Sathiya Murthy
-- Created     : 2026-07-20
-- Database    : PostgreSQL 14+ | Snowflake | Databricks SQL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXPLANATION
-- -----------------------------------------------------------------------------
-- A Recursive CTE (Common Table Expression) allows a query to reference itself,
-- enabling traversal of hierarchical or graph-like data structures stored in
-- relational tables. The structure has two members separated by UNION ALL:
--   1. ANCHOR MEMBER    : The base case — selects the root row(s)
--   2. RECURSIVE MEMBER : Joins the CTE back to itself to fetch the next level
--
-- The database engine executes this iteratively until no new rows are produced.
-- PostgreSQL uses the syntax: WITH RECURSIVE cte_name AS (...)
-- Snowflake and Databricks support the same ANSI SQL syntax.

-- -----------------------------------------------------------------------------
-- BUSINESS USE CASE
-- -----------------------------------------------------------------------------
-- Common scenarios:
--   • Employee org chart: Find all direct and indirect reports of a manager
--   • Bill of Materials (BOM): Explode a product into all sub-components
--   • Category hierarchies: e-commerce categories (Electronics > Phones > 5G)
--   • Account structures: Parent-subsidiary rollup in finance
--   • Network graph traversal: Find all reachable nodes from a starting node

-- -----------------------------------------------------------------------------
-- SCHEMA SETUP (Run once to create sample data)
-- -----------------------------------------------------------------------------

-- Employee table with self-referencing foreign key
CREATE TABLE IF NOT EXISTS employees (
    employee_id   INT           PRIMARY KEY,
    full_name     VARCHAR(100)  NOT NULL,
    job_title     VARCHAR(100)  NOT NULL,
    department    VARCHAR(50)   NOT NULL,
    manager_id    INT           REFERENCES employees(employee_id),   -- NULL for CEO
    salary        NUMERIC(10,2) NOT NULL,
    hire_date     DATE          NOT NULL
);

-- Sample Org Chart:
--   1: Alice (CEO)
--   ├── 2: Bob (CTO)
--   │   ├── 5: Eve (Backend Lead)
--   │   │   └── 9: Ivy (Senior Engineer)
--   │   └── 6: Frank (Data Lead)
--   │       ├── 10: Jack (Data Engineer)
--   │       └── 11: Kim (Data Analyst)
--   └── 3: Carol (CFO)
--   │   └── 7: Grace (Finance Manager)
--   └── 4: Dave (COO)
--       └── 8: Henry (Ops Manager)
--           └── 12: Leo (Ops Analyst)

INSERT INTO employees (employee_id, full_name, job_title, department, manager_id, salary, hire_date)
VALUES
    (1,  'Alice Johnson',  'CEO',              'Executive',    NULL, 450000.00, '2015-01-10'),
    (2,  'Bob Smith',      'CTO',              'Technology',   1,    320000.00, '2015-03-15'),
    (3,  'Carol Davis',    'CFO',              'Finance',      1,    310000.00, '2015-03-15'),
    (4,  'Dave Wilson',    'COO',              'Operations',   1,    305000.00, '2016-06-01'),
    (5,  'Eve Martinez',   'Backend Lead',     'Technology',   2,    180000.00, '2017-09-01'),
    (6,  'Frank Lee',      'Data Lead',        'Technology',   2,    190000.00, '2018-02-14'),
    (7,  'Grace Patel',    'Finance Manager',  'Finance',      3,    140000.00, '2019-04-22'),
    (8,  'Henry Brown',    'Ops Manager',      'Operations',   4,    135000.00, '2019-07-08'),
    (9,  'Ivy Chen',       'Senior Engineer',  'Technology',   5,    140000.00, '2020-01-15'),
    (10, 'Jack Taylor',    'Data Engineer',    'Technology',   6,    125000.00, '2021-03-01'),
    (11, 'Kim Anderson',   'Data Analyst',     'Technology',   6,    105000.00, '2022-06-15'),
    (12, 'Leo Thomas',     'Ops Analyst',      'Operations',   8,     95000.00, '2023-01-10')
ON CONFLICT (employee_id) DO NOTHING;

-- =============================================================================
-- QUERY 1: Full Org Chart Traversal — All Employees Under CEO
-- =============================================================================
-- Traverses all levels starting from the CEO (manager_id IS NULL)
-- Adds: depth level, breadcrumb path, total subordinate depth

WITH RECURSIVE org_chart AS (

    -- =========================================================================
    -- ANCHOR MEMBER: Start from the root (CEO has no manager)
    -- =========================================================================
    SELECT
        employee_id,
        full_name,
        job_title,
        department,
        manager_id,
        salary,
        0                           AS depth,           -- Level 0 = root
        CAST(full_name AS TEXT)     AS hierarchy_path,  -- Breadcrumb trail
        CAST(employee_id AS TEXT)   AS id_path          -- ID trail for cycle detection

    FROM employees
    WHERE manager_id IS NULL  -- Root node(s)

    UNION ALL

    -- =========================================================================
    -- RECURSIVE MEMBER: Join back to employees to get next level
    -- =========================================================================
    SELECT
        e.employee_id,
        e.full_name,
        e.job_title,
        e.department,
        e.manager_id,
        e.salary,
        oc.depth + 1                                                 AS depth,
        oc.hierarchy_path || ' > ' || e.full_name                   AS hierarchy_path,
        oc.id_path || ',' || CAST(e.employee_id AS TEXT)            AS id_path

    FROM employees e
    INNER JOIN org_chart oc
        ON e.manager_id = oc.employee_id

    -- SAFETY: Prevent infinite loops in circular graphs (optional in tree data)
    -- WHERE oc.id_path NOT LIKE '%,' || CAST(e.employee_id AS TEXT) || ',%'
)

SELECT
    depth,
    -- Visual indentation using REPEAT for easy readability
    REPEAT('    ', depth) || '├── ' || full_name               AS org_tree,
    job_title,
    department,
    salary,
    hierarchy_path
FROM org_chart
ORDER BY id_path;

-- =============================================================================
-- QUERY 2: Find All Reports Under a Specific Manager (Bob — CTO, ID=2)
-- =============================================================================
-- Use case: "Show me everyone Bob is responsible for, direct and indirect"

WITH RECURSIVE reports_under_manager AS (

    -- Anchor: Start at the target manager (Bob)
    SELECT
        employee_id,
        full_name,
        job_title,
        manager_id,
        salary,
        0       AS depth

    FROM employees
    WHERE employee_id = 2  -- Bob, the CTO

    UNION ALL

    -- Recursive: Get each level of subordinates
    SELECT
        e.employee_id,
        e.full_name,
        e.job_title,
        e.manager_id,
        e.salary,
        rum.depth + 1

    FROM employees e
    INNER JOIN reports_under_manager rum
        ON e.manager_id = rum.employee_id
)

SELECT
    depth,
    REPEAT('  ', depth) || full_name  AS indented_name,
    job_title,
    salary
FROM reports_under_manager
WHERE depth > 0  -- Exclude the root manager themselves
ORDER BY depth, full_name;

-- =============================================================================
-- QUERY 3: Find the Management Chain / Ancestry for a Leaf Node
-- =============================================================================
-- Use case: "Who does Jack (ID=10) report to, all the way to the CEO?"

WITH RECURSIVE management_chain AS (

    -- Anchor: Start at the target employee (Jack)
    SELECT
        employee_id,
        full_name,
        job_title,
        manager_id,
        0   AS level

    FROM employees
    WHERE employee_id = 10  -- Jack, the Data Engineer

    UNION ALL

    -- Recursive: Walk UP the tree to the parent
    SELECT
        e.employee_id,
        e.full_name,
        e.job_title,
        e.manager_id,
        mc.level + 1

    FROM employees e
    INNER JOIN management_chain mc
        ON e.employee_id = mc.manager_id
)

SELECT
    level,
    full_name,
    job_title
FROM management_chain
ORDER BY level DESC;  -- CEO first, then down to the employee

-- =============================================================================
-- QUERY 4: Salary Rollup — Total Salary Budget per Manager (Subtree)
-- =============================================================================
-- Business case: Calculate how much each manager's subtree costs

WITH RECURSIVE org_with_root AS (

    SELECT
        employee_id,
        full_name,
        manager_id,
        salary,
        employee_id     AS root_manager_id   -- Track which subtree root this belongs to

    FROM employees

    UNION ALL

    SELECT
        e.employee_id,
        e.full_name,
        e.manager_id,
        e.salary,
        owr.root_manager_id

    FROM employees e
    INNER JOIN org_with_root owr
        ON e.manager_id = owr.employee_id
),

subtree_budgets AS (
    SELECT
        root_manager_id,
        SUM(salary)     AS total_subtree_salary,
        COUNT(*) - 1    AS total_reports          -- Exclude the manager themselves
    FROM org_with_root
    GROUP BY root_manager_id
)

SELECT
    e.employee_id,
    e.full_name,
    e.job_title,
    e.salary                        AS own_salary,
    sb.total_subtree_salary         AS managed_budget,
    sb.total_reports                AS total_headcount,
    ROUND(
        (sb.total_subtree_salary - e.salary) / NULLIF(sb.total_reports, 0), 2
    )                               AS avg_report_salary
FROM employees e
JOIN subtree_budgets sb
    ON e.employee_id = sb.root_manager_id
ORDER BY sb.total_subtree_salary DESC;

-- =============================================================================
-- QUERY 5: Cycle Detection — Safe Recursive CTE with Depth Limit
-- =============================================================================
-- For graph data (not strict trees), cycles are possible. This pattern
-- detects and avoids them using an array of visited IDs.
-- NOTE: This uses PostgreSQL array syntax (Snowflake: use ARRAY_CONTAINS)

WITH RECURSIVE safe_traversal AS (

    SELECT
        employee_id,
        full_name,
        manager_id,
        0                               AS depth,
        ARRAY[employee_id]              AS visited_ids,
        FALSE                           AS is_cycle

    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    SELECT
        e.employee_id,
        e.full_name,
        e.manager_id,
        st.depth + 1,
        st.visited_ids || e.employee_id,
        e.employee_id = ANY(st.visited_ids)   -- Cycle if ID already visited

    FROM employees e
    JOIN safe_traversal st
        ON e.manager_id = st.employee_id
    WHERE
        NOT st.is_cycle           -- Stop if cycle already detected
        AND st.depth < 20         -- Hard depth limit as safety net
)

SELECT
    employee_id,
    full_name,
    depth,
    is_cycle
FROM safe_traversal
WHERE is_cycle = TRUE;   -- Should return 0 rows for clean tree data

-- =============================================================================
-- PERFORMANCE NOTES
-- =============================================================================
-- 1. Index on manager_id is CRITICAL for recursive CTEs:
CREATE INDEX IF NOT EXISTS idx_employees_manager_id ON employees(manager_id);

-- 2. For very deep trees (>100 levels), increase max_recursion parameter:
--    PostgreSQL: SET statement_timeout = '60s';  -- prevent runaway queries

-- 3. Recursive CTEs are evaluated as iterative loops internally — NOT actual
--    recursion. Each iteration produces a "working table" joined back.

-- 4. PostgreSQL materializes CTEs by default (MATERIALIZED keyword).
--    For recursive CTEs, this is mandatory — the engine always materializes.

-- 5. If your tree has millions of nodes, consider:
--    a) Closure Table pattern (pre-computed ancestor/descendant pairs)
--    b) Nested Sets (left/right encodings)
--    c) ltree extension (PostgreSQL-specific path-based hierarchy)

-- =============================================================================
-- OPTIMIZATION TIPS
-- =============================================================================
-- TIP 1: Add WHERE clause in the recursive member to prune early
-- TIP 2: Use depth limit (depth < N) to avoid accidental infinite loops
-- TIP 3: If querying subtrees often, materialize the closure table nightly
-- TIP 4: Use id_path string trick for cycle detection without arrays (portable)
-- TIP 5: SELECT only needed columns — recursive CTEs copy full row each iteration

-- =============================================================================
-- COMMON MISTAKES
-- =============================================================================
-- MISTAKE 1: Forgetting UNION ALL (using UNION) — removes valid duplicate paths
-- MISTAKE 2: Missing index on the join column (manager_id) — causes table scans
-- MISTAKE 3: No depth limit on graph data — runs forever on cycles
-- MISTAKE 4: Selecting * in recursive member — carries massive row width
-- MISTAKE 5: Confusing anchor vs recursive member ordering — anchor must be first

-- =============================================================================
-- INTERVIEW QUESTIONS
-- =============================================================================
-- Q1: What is the difference between the anchor member and recursive member in a CTE?
--     A: The anchor produces the base result set. The recursive member self-references
--        the CTE and is joined to produce the next iteration's rows. Execution stops
--        when the recursive member returns no new rows.

-- Q2: Why must we use UNION ALL and not UNION in recursive CTEs?
--     A: UNION removes duplicates by doing a hash comparison each iteration, adding
--        massive overhead. Duplicate paths in hierarchies are valid (e.g., same node
--        reachable via multiple paths in a graph). Use UNION only if cycle prevention
--        requires deduplication.

-- Q3: How would you find all leaf nodes (employees with no reports)?
--     A: SELECT e.employee_id FROM employees e
--        WHERE NOT EXISTS (SELECT 1 FROM employees sub WHERE sub.manager_id = e.employee_id)

-- Q4: What is the Closure Table pattern and when would you prefer it over recursive CTEs?
--     A: Closure Table pre-stores all ancestor-descendant pairs with path lengths.
--        Prefer it when: (1) hierarchy is queried frequently, (2) tree is large and
--        deep, (3) you need to avoid recursive query overhead in production.

-- Q5: How does Snowflake's CONNECT BY differ from WITH RECURSIVE?
--     A: CONNECT BY is Oracle-style hierarchical syntax. Snowflake supports both
--        WITH RECURSIVE (ANSI standard) and CONNECT BY (Oracle compat mode).
--        WITH RECURSIVE is preferred for portability.
