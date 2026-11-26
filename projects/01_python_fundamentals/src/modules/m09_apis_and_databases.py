"""
Module 32-34: REST API Integration, Rate Limiting, and SQLite Database Operations.

Explanation:
Extract data from third-party REST APIs or relational database systems safely using transactional connections.

Business Use Case:
Fetch employee metadata from SQLite table and format as analytical dataset.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any

def fetch_employees_from_sqlite(db_path: Path) -> List[Dict[str, Any]]:
    """Query employee records from SQLite database."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, department, salary, hire_date FROM employees WHERE salary > 110000")
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]

    conn.close()
    return results
