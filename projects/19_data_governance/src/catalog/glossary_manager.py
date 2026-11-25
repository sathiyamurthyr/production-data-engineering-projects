"""
Glossary Manager Module
=======================
Manages the Business Glossary (glossary terms, definitions, categories, and business owner assignments).
"""

import sqlite3
import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class GlossaryTerm:
    """Represents a term in the corporate Business Glossary."""
    term_name: str
    definition: str
    category: str
    owner: str
    sensitivity_level: str = "PUBLIC"


class GlossaryManager:
    """
    Manages the Business Glossary in the data catalog.
    """
    def __init__(self, db_path: str = "data_catalog.db"):
        self.db_path = db_path
        self._init_glossary_table()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_glossary_table(self):
        """Initializes the business glossary table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS business_glossary (
                    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term_name TEXT NOT NULL UNIQUE,
                    definition TEXT NOT NULL,
                    category TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    sensitivity_level TEXT DEFAULT 'PUBLIC',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_glossary_term ON business_glossary(term_name)")
            conn.commit()

    def create_term(self, term: Any) -> int:
        """
        Creates a new term in the business glossary.
        
        Args:
            term: GlossaryTerm object or a dictionary.
            
        Returns:
            The created term_id.
        """
        if isinstance(term, GlossaryTerm):
            term_dict = {
                "term_name": term.term_name,
                "definition": term.definition,
                "category": term.category,
                "owner": term.owner,
                "sensitivity_level": term.sensitivity_level
            }
        else:
            term_dict = term

        query = """
            INSERT INTO business_glossary (term_name, definition, category, owner, sensitivity_level)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(term_name) DO UPDATE SET
                definition = excluded.definition,
                category = excluded.category,
                owner = excluded.owner,
                sensitivity_level = excluded.sensitivity_level
        """
        params = (
            term_dict["term_name"],
            term_dict["definition"],
            term_dict["category"],
            term_dict["owner"],
            term_dict.get("sensitivity_level", "PUBLIC")
        )
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            
            cursor.execute("SELECT term_id FROM business_glossary WHERE term_name = ?", (term_dict["term_name"],))
            row = cursor.fetchone()
            return row["term_id"] if row else -1

    def get_term_by_name(self, term_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a term by its name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM business_glossary WHERE term_name = ?", (term_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_terms(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all glossary terms, optionally filtering by category."""
        if category:
            query = "SELECT * FROM business_glossary WHERE category = ?"
            params = (category,)
        else:
            query = "SELECT * FROM business_glossary"
            params = ()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def delete_term(self, term_name: str) -> bool:
        """Deletes a glossary term."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM business_glossary WHERE term_name = ?", (term_name,))
            conn.commit()
            return True
