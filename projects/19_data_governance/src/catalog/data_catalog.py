"""
Data Catalog Module
===================
Manages physical and logical metadata catalogs, schema storage, and catalog entries
for data assets inside the enterprise data governance ecosystem.
"""

import sqlite3
import logging
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)

@dataclass
class CatalogEntry:
    """Represents a logical data asset entry in the catalog (e.g., a table)."""
    asset_id: str
    asset_name: str
    domain: str
    owner: str
    asset_type: str = "table"
    sensitivity_level: str = "PUBLIC"
    storage_location: str = ""
    description: str = "No description"
    schema_fields: Dict[str, str] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Converts the catalog entry to a flat dictionary."""
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "domain": self.domain,
            "owner": self.owner,
            "asset_type": self.asset_type,
            "sensitivity_level": self.sensitivity_level,
            "storage_location": self.storage_location,
            "description": self.description,
            "schema_fields": self.schema_fields,
            "tags": list(self.tags),
            "created_at": self.created_at
        }


class DataCatalog:
    """
    Manages the physical metadata store (SQLite) for the Data Governance Catalog.
    Provides APIs for creating tables, registering schemas, tables, columns, and search.
    """
    def __init__(self, db_path: str = "data_catalog.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        """Initializes database tables if they do not exist."""
        logger.info(f"Initializing data catalog database at: {self.db_path}")
        
        # Ensure directories exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Column-level Data Assets Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_assets (
                    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    database_name TEXT NOT NULL,
                    schema_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    description TEXT,
                    owner TEXT,
                    business_domain TEXT,
                    sensitivity_level TEXT DEFAULT 'PUBLIC',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(database_name, schema_name, table_name, column_name)
                )
            """)

            # Indexing for faster catalog search
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_table ON data_assets(database_name, schema_name, table_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_sensitivity ON data_assets(sensitivity_level)")
            
            # 2. Table-level Catalog Entries Table (supports CatalogEntry objects)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS catalog_entries (
                    asset_id TEXT PRIMARY KEY,
                    asset_name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    sensitivity_level TEXT NOT NULL,
                    storage_location TEXT,
                    description TEXT,
                    schema_fields TEXT,  -- JSON representation
                    tags TEXT,           -- JSON list representation
                    created_at TEXT
                )
            """)
            
            conn.commit()

    def register_asset(self, asset: Any) -> Any:
        """
        Registers or updates a data asset or a column in the data catalog.
        Accepts either a CatalogEntry object or a dictionary.
        
        Args:
            asset: Dict containing database_name, schema_name, table_name, column_name etc.,
                   OR a CatalogEntry object.
                   
        Returns:
            The registered asset ID (integer for columns, string for CatalogEntry).
        """
        if isinstance(asset, CatalogEntry):
            return self._register_catalog_entry(asset)
        elif isinstance(asset, dict):
            return self._register_column_asset(asset)
        else:
            raise TypeError("Asset must be a CatalogEntry or a dictionary.")

    def _register_catalog_entry(self, entry: CatalogEntry) -> str:
        """Inserts or updates a CatalogEntry in the database."""
        query = """
            INSERT INTO catalog_entries (
                asset_id, asset_name, domain, owner, asset_type, sensitivity_level,
                storage_location, description, schema_fields, tags, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                asset_name = excluded.asset_name,
                domain = excluded.domain,
                owner = excluded.owner,
                asset_type = excluded.asset_type,
                sensitivity_level = excluded.sensitivity_level,
                storage_location = excluded.storage_location,
                description = excluded.description,
                schema_fields = excluded.schema_fields,
                tags = excluded.tags,
                created_at = excluded.created_at
        """
        params = (
            entry.asset_id,
            entry.asset_name,
            entry.domain,
            entry.owner,
            entry.asset_type,
            entry.sensitivity_level,
            entry.storage_location,
            entry.description,
            json.dumps(entry.schema_fields),
            json.dumps(list(entry.tags)),
            entry.created_at
        )
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            logger.info(f"Registered CatalogEntry '{entry.asset_name}' [{entry.asset_id}]")
            return entry.asset_id

    def _register_column_asset(self, asset: Dict[str, Any]) -> int:
        """Inserts or updates a column asset (dictionary-based)."""
        query = """
            INSERT INTO data_assets (
                database_name, schema_name, table_name, column_name, data_type, description, owner, business_domain, sensitivity_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(database_name, schema_name, table_name, column_name) DO UPDATE SET
                data_type = excluded.data_type,
                description = COALESCE(excluded.description, description),
                owner = COALESCE(excluded.owner, owner),
                business_domain = COALESCE(excluded.business_domain, business_domain),
                sensitivity_level = COALESCE(excluded.sensitivity_level, sensitivity_level),
                last_updated = CURRENT_TIMESTAMP
        """
        params = (
            asset["database_name"],
            asset["schema_name"],
            asset["table_name"],
            asset["column_name"],
            asset["data_type"],
            asset.get("description"),
            asset.get("owner"),
            asset.get("business_domain"),
            asset.get("sensitivity_level", "PUBLIC")
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            
            cursor.execute("""
                SELECT asset_id FROM data_assets 
                WHERE database_name = ? AND schema_name = ? AND table_name = ? AND column_name = ?
            """, (asset["database_name"], asset["schema_name"], asset["table_name"], asset["column_name"]))
            row = cursor.fetchone()
            return row["asset_id"] if row else -1

    def get_asset_by_id(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves column asset detail by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM data_assets WHERE asset_id = ?", (asset_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_asset_by_path(self, db: str, schema: str, table: str, col: str) -> Optional[Dict[str, Any]]:
        """Retrieves column asset detail by path query."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM data_assets 
                WHERE database_name = ? AND schema_name = ? AND table_name = ? AND column_name = ?
            """, (db, schema, table, col))
            row = cursor.fetchone()
            return dict(row) if row else None

    def search_assets(self, query_str: str) -> List[Dict[str, Any]]:
        """Searches column assets by string matching database, table, column, or description."""
        like_query = f"%{query_str}%"
        sql = """
            SELECT * FROM data_assets 
            WHERE database_name LIKE ? 
               OR schema_name LIKE ? 
               OR table_name LIKE ? 
               OR column_name LIKE ? 
               OR description LIKE ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (like_query, like_query, like_query, like_query, like_query))
            return [dict(row) for row in cursor.fetchall()]

    def list_all_assets(self) -> List[Dict[str, Any]]:
        """Lists all column data assets."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM data_assets")
            return [dict(row) for row in cursor.fetchall()]

    def list_all(self) -> List[CatalogEntry]:
        """Lists all table-level CatalogEntry objects (used by compliance reporter)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM catalog_entries")
            rows = cursor.fetchall()
            entries = []
            for r in rows:
                schema_fields = json.loads(r["schema_fields"]) if r["schema_fields"] else {}
                tags = set(json.loads(r["tags"])) if r["tags"] else set()
                entries.append(CatalogEntry(
                    asset_id=r["asset_id"],
                    asset_name=r["asset_name"],
                    domain=r["domain"],
                    owner=r["owner"],
                    asset_type=r["asset_type"],
                    sensitivity_level=r["sensitivity_level"],
                    storage_location=r["storage_location"],
                    description=r["description"],
                    schema_fields=schema_fields,
                    tags=tags,
                    created_at=r["created_at"]
                ))
            return entries

    def update_sensitivity(self, asset_id: Any, level: str):
        """Updates the sensitivity level classification of a registered asset (column or CatalogEntry)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if isinstance(asset_id, int) or (isinstance(asset_id, str) and asset_id.isdigit()):
                cursor.execute("""
                    UPDATE data_assets 
                    SET sensitivity_level = ?, last_updated = CURRENT_TIMESTAMP 
                    WHERE asset_id = ?
                """, (level, int(asset_id)))
            else:
                cursor.execute("""
                    UPDATE catalog_entries 
                    SET sensitivity_level = ? 
                    WHERE asset_id = ?
                """, (level, str(asset_id)))
            conn.commit()
