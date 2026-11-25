"""
================================================================================
MODULE 34: SQLite Relational Database Operations
================================================================================
1. EXPLANATION:
SQLite provides lightweight embedded SQL database functionality for staging local pipeline metadata.

2. BUSINESS USE CASE:
Query relational database tables using SQL parameters to prevent SQL injection.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

def query_sqlite_employees(db_path: Path) -> List[Dict[str, Any]]:
    """Query employee table from SQLite DB."""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, department, salary FROM employees WHERE salary >= ?", (110000.0,))
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results
