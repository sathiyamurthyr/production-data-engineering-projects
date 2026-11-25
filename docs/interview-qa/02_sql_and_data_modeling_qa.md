# 02. SQL & Data Modeling — Interview Q&A

---

### Q1: Generate every unique match pairing from a `table_team` country table (e.g., `IND VS PAK`, no reverse duplicates or self-matches).
**Answer:** Use a non-equi self-join on `a.team_id < b.team_id`:
```sql
SELECT
    a.team_name || ' VS ' || b.team_name AS match_up
FROM table_team a
JOIN table_team b
    ON a.team_id < b.team_id;
```
*(In MySQL/Snowflake/Spark SQL where `||` may not concatenate strings, use `CONCAT(a.team_name, ' VS ', b.team_name)`.)*

---

### Q2: Find employees earning more than their department's average salary.
**Answer:**
```sql
-- Option 1: Correlated Subquery
SELECT EmployeeID, DepartmentID, Salary
FROM tblEmployeeInfo AS T1
WHERE Salary > (
    SELECT AVG(Salary)
    FROM tblEmployeeInfo AS T2
    WHERE T1.DepartmentID = T2.DepartmentID
);

-- Option 2: Window Function (usually faster — single table scan)
SELECT EmployeeID, DepartmentID, Salary
FROM (
    SELECT
        EmployeeID,
        DepartmentID,
        Salary,
        AVG(Salary) OVER (PARTITION BY DepartmentID) AS dept_avg_sal
    FROM tblEmployeeInfo
) t
WHERE Salary > dept_avg_sal;
```

---

### Q3: Find the average salary of departments having more than 5 employees.
**Answer:**
```sql
SELECT
    DEPARTMENT,
    COUNT(STAFF_ID) AS CountStaff,
    AVG(SALARY) AS AVGSalary
FROM STAFF
GROUP BY DEPARTMENT
HAVING COUNT(STAFF_ID) > 5;
```

---

### Q4: Find the 2nd (or Nth) highest salary using Window Functions (`RANK` vs `DENSE_RANK`).
**Answer:**
- **`DENSE_RANK()`** is preferred when two employees tie for 1st place and you still want the next distinct salary as 2nd (`1, 1, 2`).
- **`RANK()`** skips numbers after ties (`1, 1, 3`).

```sql
-- 2nd highest distinct salary (overall)
SELECT salary
FROM (
    SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS rnk
    FROM employee
) ranked_salaries
WHERE rnk = 2;
```

---

### Q5: How do you find or deduplicate duplicate rows in SQL?
**Answer:**
```sql
-- Keep the latest record per id
SELECT *
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY id ORDER BY date DESC) AS rnk
    FROM emp
) t
WHERE rnk = 1;

-- Count unique IDs / detect duplicates
SELECT id, COUNT(*) AS dup_count
FROM emp
GROUP BY id
HAVING COUNT(*) > 1;
```

---

### Q6: Find customers who placed orders in 3 consecutive months.
**Answer:**
Use `LAG()` or `ROW_NUMBER()` over distinct `(year, month)` index `(YEAR * 12 + MONTH) - ROW_NUMBER()` (Gaps & Islands pattern):
```sql
WITH distinct_months AS (
    SELECT DISTINCT
        customer_id,
        (EXTRACT(YEAR FROM order_date) * 12 + EXTRACT(MONTH FROM order_date)) AS ym_num
    FROM orders
),
grouped AS (
    SELECT
        customer_id,
        ym_num,
        ym_num - ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY ym_num) AS grp
    FROM distinct_months
)
SELECT DISTINCT customer_id
FROM grouped
GROUP BY customer_id, grp
HAVING COUNT(*) >= 3;
```

---

### Q7: Explain `LEAD()` and `LAG()` window functions with a time-series use case.
**Answer:**
- **`LAG(col, offset, default)`** reads a value from a **previous** row within the partition without a self-join.
- **`LEAD(col, offset, default)`** reads a value from a **subsequent** row.
- **Time-series use case:** Calculate Month-over-Month (MoM) revenue growth or detect session gaps between consecutive user clicks:
```sql
SELECT
    order_month,
    revenue,
    LAG(revenue) OVER (ORDER BY order_month) AS prev_month_rev,
    revenue - LAG(revenue) OVER (ORDER BY order_month) AS mom_delta
FROM monthly_sales;
```

---

### Q8: What is a Materialized View, and how does it differ from a standard View?
**Answer:**
- **Standard View:** Saved SQL query executed dynamically on every read; stores zero data.
- **Materialized View:** Precomputes and **physically persists** query results on disk, giving fast read latency for expensive joins/aggregations at the cost of storage and periodic/incremental refresh overhead.

---

### Q9: Explain all SQL Join types (`INNER`, `LEFT`, `RIGHT`, `FULL OUTER`, `CROSS`, `LEFT SEMI`, `LEFT ANTI`, `SELF`).
**Answer:**
| Join Type | Behavior |
|---|---|
| **`INNER`** | Returns only rows matching in both tables. |
| **`LEFT` (`LEFT OUTER`)** | All rows from left table + matched right rows (`NULL` if no match). |
| **`RIGHT` (`RIGHT OUTER`)** | All rows from right table + matched left rows (`NULL` if no match). |
| **`FULL OUTER`** | All rows from both tables; unmatched sides filled with `NULL`. |
| **`CROSS`** | Cartesian product ($M \times N$ combinations). |
| **`LEFT SEMI`** | Rows from left table that have **at least one** match in right (returns left columns only, no row duplication). |
| **`LEFT ANTI`** | Rows from left table that have **no** match in right (great for delta/missing-record checks). |
| **`SELF`** | Joins a table to itself using aliases (`a` and `b`) for hierarchies or pair comparisons. |

---

### Q10: Compare Star, Snowflake, and Galaxy (Fact Constellation) Schemas.
**Answer:**
- **Star Schema:** Central Fact table surrounded by **denormalized** Dimension tables. Fewer joins, fastest BI query performance, industry default for analytics marts.
- **Snowflake Schema:** Dimension tables are **normalized** into sub-dimensions (e.g., `Product -> Subcategory -> Category`). Reduces redundancy/storage, increases join depth.
- **Galaxy (Fact Constellation) Schema:** Multiple Fact tables (e.g., `fact_orders` and `fact_shipments`) sharing **conformed Dimension tables** (`dim_customer`, `dim_date`) across enterprise data warehouses.
