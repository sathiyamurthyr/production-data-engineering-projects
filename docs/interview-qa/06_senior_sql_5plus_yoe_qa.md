# 06. Senior SQL Interview Questions & Concepts (5+ Years Experience)

Curated SQL coding patterns and conceptual deep dives commonly asked in **Senior Data Engineer**, **Databricks SQL**, and **Cloud Data Warehouse** interviews.

---

## Part A: 25 Must-Know Senior SQL Query Patterns

### 1. Find the 2nd Highest Salary
```sql
SELECT MAX(salary) AS second_highest_salary
FROM employee
WHERE salary < (SELECT MAX(salary) FROM employee);
```
> **Edge Case:** Returns `NULL` if all employees earn the same salary or the table has `< 2` rows.

---

### 2. Find the Nth Highest Salary (e.g., 5th Highest)
```sql
SELECT DISTINCT salary
FROM (
    SELECT salary,
           DENSE_RANK() OVER (ORDER BY salary DESC) AS rnk
    FROM employee
) t
WHERE rnk = 5;
```
> **Tip:** Add `DISTINCT` so ties at rank 5 return a single scalar row. Use `DENSE_RANK()` instead of `ROW_NUMBER()` when duplicate salaries exist.

---

### 3. Remove Duplicate Records
```sql
-- Portable SQL (MySQL / PostgreSQL / SQLite)
DELETE FROM employee
WHERE id NOT IN (
    SELECT min_id
    FROM (
        SELECT MIN(id) AS min_id
        FROM employee
        GROUP BY emp_name
    ) keep_rows
);

-- Preferred in PostgreSQL / Snowflake / Databricks (handles large tables & NULLs safely)
DELETE FROM employee e
USING (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY emp_name ORDER BY id) AS rn
    FROM employee
) d
WHERE e.id = d.id AND d.rn > 1;
```
> **Edge Case:** Avoid `NOT IN` if the subquery can ever return `NULL` (prefer `NOT EXISTS` or `ROW_NUMBER()`).

---

### 4. Find Duplicate Records
```sql
SELECT emp_name,
       COUNT(*) AS dup_count
FROM employee
GROUP BY emp_name
HAVING COUNT(*) > 1;
```

---

### 5. Find Employees Without Managers
```sql
SELECT *
FROM employee
WHERE manager_id IS NULL;
```

---

### 6. Employees Earning More Than Their Managers
```sql
SELECT e.emp_name,
       e.salary,
       m.emp_name AS manager,
       m.salary   AS manager_salary
FROM employee e
JOIN employee m
  ON e.manager_id = m.id
WHERE e.salary > m.salary;
```

---

### 7. Running Total
```sql
SELECT emp_id,
       salary,
       SUM(salary) OVER (
           ORDER BY emp_id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_total
FROM employee;
```
> **Senior Tip:** Always specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` if `ORDER BY` has ties—the SQL default `RANGE` frame adds all tied rows together at once!

---

### 8. Department-Wise Highest Salary
```sql
SELECT *
FROM (
    SELECT *,
           DENSE_RANK() OVER (
               PARTITION BY department
               ORDER BY salary DESC
           ) AS rnk
    FROM employee
) t
WHERE rnk = 1;
```

---

### 9. Third Highest Salary in Every Department
```sql
SELECT *
FROM (
    SELECT *,
           DENSE_RANK() OVER (
               PARTITION BY department
               ORDER BY salary DESC
           ) AS rnk
    FROM employee
) t
WHERE rnk = 3;
```

---

### 10. Top 3 Salaries Per Department
```sql
SELECT *
FROM (
    SELECT *,
           DENSE_RANK() OVER (
               PARTITION BY department
               ORDER BY salary DESC
           ) AS rnk
    FROM employee
) x
WHERE rnk <= 3;
```

---

### 11. Find Missing IDs (Immediate Gap Detection)
Sample data: `1, 2, 3, 5, 6, 8`
```sql
SELECT t1.id + 1 AS missing_id
FROM numbers t1
LEFT JOIN numbers t2
  ON t1.id + 1 = t2.id
WHERE t2.id IS NULL
  AND t1.id < (SELECT MAX(id) FROM numbers);
```
> **Note:** Adding `t1.id < (SELECT MAX(id) FROM numbers)` prevents `MAX(id) + 1` (`9`) from being falsely reported as missing. For multi-number gaps (e.g., `1` → `5`), use `LEAD(id)` or a Recursive CTE / `GENERATE_SERIES(1, MAX(id))`.

---

### 12. Consecutive Duplicate Values
```sql
SELECT *
FROM (
    SELECT *,
           LAG(status) OVER (ORDER BY id) AS prev_status
    FROM orders
) t
WHERE status = prev_status;
```

---

### 13. First Order of Every Customer
```sql
SELECT *
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY order_date ASC, order_id ASC
           ) AS rn
    FROM orders
) t
WHERE rn = 1;
```

---

### 14. Latest Record Per Customer
```sql
SELECT *
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY order_date DESC, order_id DESC
           ) AS rn
    FROM orders
) t
WHERE rn = 1;
```

---

### 15. Pivot Example (Conditional Aggregation)
```sql
SELECT
    SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) AS Male,
    SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) AS Female
FROM employee;
```
> **Tip:** Portable across all SQL dialects (PostgreSQL, SQLite, Snowflake, Spark SQL) unlike vendor-specific `PIVOT` syntax.

---

### 16. Unpivot Example (`UNION ALL`)
```sql
SELECT id, 'Math' AS Subject, MathMarks AS Marks
FROM student

UNION ALL

SELECT id, 'Science' AS Subject, ScienceMarks AS Marks
FROM student;
```
> **Note:** Use `UNION ALL` (not `UNION`) to avoid an unnecessary `DISTINCT` sort shuffle. On Spark/Snowflake you can also use `LATERAL VIEW stack(...)` / `UNPIVOT`.

---

### 17. Find Gap Between Dates
```sql
WITH ordered_dates AS (
    SELECT order_id,
           order_date,
           LAG(order_date) OVER (ORDER BY order_date) AS previous_date
    FROM orders
)
SELECT order_id,
       order_date,
       previous_date,
       DATEDIFF(order_date, previous_date) AS diff_days  -- Spark/MySQL; Snowflake: DATEDIFF('day', prev, curr); Postgres: order_date - previous_date
FROM ordered_dates;
```

---

### 18. Monthly Sales Aggregation
```sql
SELECT
    YEAR(order_date)  AS sales_year,
    MONTH(order_date) AS sales_month,
    SUM(amount)       AS total_sales
FROM sales
GROUP BY
    YEAR(order_date),
    MONTH(order_date)
ORDER BY sales_year, sales_month;
```
> **SARGability Tip:** Prefer `DATE_TRUNC('month', order_date)` when returning a single sortable date column.

---

### 19. Moving Average (3-Row Rolling Window)
```sql
SELECT
    order_date,
    AVG(amount) OVER (
        ORDER BY order_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS moving_avg_3
FROM sales;
```

---

### 20. Cumulative Sum
```sql
SELECT
    order_date,
    SUM(amount) OVER (
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_sum
FROM sales;
```

---

### 21. Customers With No Orders
```sql
SELECT c.customer_id
FROM customers c
LEFT JOIN orders o
  ON c.customer_id = o.customer_id
WHERE o.customer_id IS NULL;

-- Alternative (often clearer intent / semi-anti optimization)
SELECT c.customer_id
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
);
```

---

### 22. Find Common Records (`INTERSECT`)
```sql
SELECT * FROM table1
INTERSECT
SELECT * FROM table2;
```
> **Note:** Both queries must have the same number of columns and compatible types. `INTERSECT` deduplicates by default (`INTERSECT ALL` keeps duplicates).

---

### 23. Find Unmatched Records (`EXCEPT` / `MINUS`)
```sql
SELECT * FROM table1
EXCEPT
SELECT * FROM table2;
```
*(Oracle uses `MINUS` instead of `EXCEPT`.)*

---

### 24. Recursive CTE (Employee Hierarchy)
```sql
WITH RECURSIVE emp_tree AS (
    -- Anchor member: top-level managers
    SELECT id,
           emp_name,
           manager_id,
           0 AS level
    FROM employee
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive member: direct reports
    SELECT e.id,
           e.emp_name,
           e.manager_id,
           t.level + 1 AS level
    FROM employee e
    JOIN emp_tree t
      ON e.manager_id = t.id
)
SELECT *
FROM emp_tree;
```

---

### 25. Find Employees Joined in the Last 30 Days
```sql
-- Standard ANSI / PostgreSQL / Databricks SQL
SELECT *
FROM employee
WHERE joining_date >= CURRENT_DATE - INTERVAL '30' DAY;

-- Spark SQL / MySQL alternative: DATE_SUB(CURRENT_DATE(), 30)
```

---

## Part B: Frequently Asked SQL Concepts (5+ YOE) — Clear Answers

### 1. Difference between `ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()`
For tied values `(100, 100, 90)`:
- **`ROW_NUMBER()`:** `1, 2, 3` (always unique, arbitrary tie-break unless `ORDER BY` includes a unique key).
- **`RANK()`:** `1, 1, 3` (same rank for ties, **skips** subsequent numbers).
- **`DENSE_RANK()`:** `1, 1, 2` (same rank for ties, **no gaps**).

### 2. `INNER JOIN` vs `LEFT JOIN` vs `RIGHT JOIN` vs `FULL OUTER JOIN`
- **`INNER JOIN`:** Intersection — only matching keys from both tables.
- **`LEFT JOIN`:** All left rows + matched right rows (`NULL` where right has no match).
- **`RIGHT JOIN`:** All right rows + matched left rows (`NULL` where left has no match).
- **`FULL OUTER JOIN`:** Union of both — all rows from both sides, `NULL` on whichever side lacks a match.

### 3. `UNION` vs `UNION ALL`
- **`UNION`:** Combines result sets and **removes duplicates** (requires an expensive sort/hash `DISTINCT` pass).
- **`UNION ALL`:** Appends result sets **as-is including duplicates** — significantly faster and preferred when inputs are disjoint or duplicates are valid.

### 4. `EXISTS` vs `IN`
- **`IN`:** Compares a value against a list/subquery; **breaks silently if the subquery returns `NULL`** with `NOT IN` (evaluates to `UNKNOWN` and returns 0 rows!).
- **`EXISTS`:** Evaluates boolean existence and **short-circuits on the first matching row**; safe with `NULL`s (`NOT EXISTS` works reliably even when nullable keys exist).

### 5. `DELETE` vs `TRUNCATE` vs `DROP`
- **`DELETE` (DML):** Removes filtered rows (`WHERE`), logs each row for rollback, fires triggers, keeps table structure.
- **`TRUNCATE` (DDL):** Deallocates all data pages instantly, resets identity/high-water marks, minimal logging, keeps table schema.
- **`DROP` (DDL):** Permanently removes **both** data and table schema/metadata/indexes from the catalog.

### 6. `WHERE` vs `HAVING`
- **`WHERE`:** Filters **individual rows before** `GROUP BY` and aggregations (cannot reference `SUM()`, `COUNT()`).
- **`HAVING`:** Filters **aggregated groups after** `GROUP BY` (e.g., `HAVING COUNT(*) > 5`).

### 7. Common Table Expressions (CTEs)
A named temporary result set defined via `WITH cte_name AS (...)` scoped to a single SQL statement. Improves readability, modularity, and avoids repeating subqueries—and in modern optimizers (Postgres 12+, Snowflake, Spark SQL), CTEs are inlined unless materialized.

### 8. Recursive CTEs
A CTE referencing itself (`Anchor UNION ALL Recursive`) used to traverse trees/graphs (org charts, bill-of-materials, category hierarchies) or generate number/date spines. Must have a termination condition (and cycle guard if data can loop).

### 9. Window Functions (`LAG`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`)
Perform calculations across a sliding frame (`OVER (PARTITION BY ... ORDER BY ...)`) **without collapsing rows** like `GROUP BY`.
- `LAG` / `LEAD`: Access previous / next row values.
- `FIRST_VALUE` / `LAST_VALUE`: Return first / last value in the window frame (**Pitfall:** `LAST_VALUE` defaults to `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, so you must explicitly add `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`!).

### 10. Correlated vs Non-Correlated Subqueries
- **Non-Correlated:** Inner query runs independently **once**, returning values to the outer query.
- **Correlated:** Inner query references a column from the outer row (`WHERE T1.dept = T2.dept`) and conceptually re-evaluates per outer row unless the optimizer rewrites it into a join/semi-join.

### 11. Indexes and Query Optimization
- **B-Tree Indexes** speed up point lookups and range scans on OLTP tables; **Columnar Micro-Partitions / Z-Order / Liquid Clustering** handle data skipping in OLAP/Lakehouses.
- **Golden Rules:** Write **SARGable** predicates (`col >= '2026-01-01'` instead of `YEAR(col) = 2026`), project only needed columns (`SELECT col1, col2` instead of `SELECT *`), filter early before joins, and partition/cluster on frequent filter keys.

### 12. Execution Plans and Performance Tuning
Inspect `EXPLAIN` / `EXPLAIN ANALYZE` (or Spark UI SQL DAG) to spot:
- Full Table Scans where an index/partition prune should happen.
- Costly **Hash/Sort-Merge Shuffles** (`DS_DIST_BOTH` / wide exchange) instead of Broadcast or Colocated joins.
- Memory spills to disk (`tempdb` / external merge sort) due to skewed keys or stale table statistics (`ANALYZE TABLE`).

### 13. ACID Properties and Transaction Isolation Levels
- **ACID:** **Atomicity** (all-or-nothing), **Consistency** (constraints preserved), **Isolation** (concurrent transactions don't corrupt each other), **Durability** (committed writes survive crashes).
- **Isolation Levels (weakest → strongest):**
  1. `READ UNCOMMITTED` (allows dirty reads)
  2. `READ COMMITTED` (prevents dirty reads; allows non-repeatable & phantom reads)
  3. `REPEATABLE READ` (snapshot/locks prevent non-repeatable reads; InnoDB/MVCC also prevents phantoms)
  4. `SERIALIZABLE` (strictly equivalent to serial execution; prevents dirty, non-repeatable, and phantom reads, at higher lock/retry contention).
