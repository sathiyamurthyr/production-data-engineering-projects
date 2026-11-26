"""
Metadata Manager Module
=======================
Handles metadata ingestion, bulk uploads, schema discovery, and asset tagging.
"""

import csv
import logging
import sqlite3
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from src.catalog.data_catalog import DataCatalog

logger = logging.getLogger(__name__)

@dataclass
class ColumnMetadata:
    """Represents physical column-level governance metadata."""
    column_name: str
    data_type: str
    description: Optional[str] = None
    sensitivity_level: str = "PUBLIC"


@dataclass
class DataAsset:
    """Represents a dataset asset containing columns and ownership metadata."""
    asset_id: str
    database_name: str
    schema_name: str
    table_name: str
    columns: List[ColumnMetadata] = field(default_factory=list)
    owner: str = "UNKNOWN"
    business_domain: str = "general"


class MetadataManager:
    """
    Manages schemas, schema discovery, bulk metadata ingestion, and tagging of metadata assets.
    """
    def __init__(self, catalog: DataCatalog):
        self.catalog = catalog
        self._init_metadata_tables()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.catalog.db_path)

    def _init_metadata_tables(self):
        """Initializes the metadata tagging tables in the SQLite database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS asset_tags (
                    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    tag_key TEXT NOT NULL,
                    tag_value TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(asset_id) REFERENCES data_assets(asset_id) ON DELETE CASCADE,
                    UNIQUE(asset_id, tag_key)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_asset ON asset_tags(asset_id)")
            conn.commit()

    def ingest_from_csv(self, csv_filepath: str) -> int:
        """
        Bulk ingests metadata assets from an inventory CSV file.
        
        Args:
            csv_filepath: Path to the inventory CSV file.
            
        Returns:
            Number of assets successfully registered.
        """
        logger.info(f"Ingesting metadata assets from: {csv_filepath}")
        count = 0
        try:
            with open(csv_filepath, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    asset = {
                        "database_name": row["database_name"],
                        "schema_name": row["schema_name"],
                        "table_name": row["table_name"],
                        "column_name": row["column_name"],
                        "data_type": row["data_type"],
                        "description": row.get("description"),
                        "owner": row.get("owner"),
                        "business_domain": row.get("business_domain"),
                        "sensitivity_level": row.get("sensitivity_level", "PUBLIC")
                    }
                    self.catalog.register_asset(asset)
                    count += 1
            logger.info(f"Successfully ingested {count} assets.")
        except Exception as e:
            logger.error(f"Error during metadata ingestion: {str(e)}")
            raise e
        return count

    def add_tag(self, asset_id: int, key: str, value: str):
        """Adds or updates a tag key-value pair on a data asset."""
        query = """
            INSERT INTO asset_tags (asset_id, tag_key, tag_value)
            VALUES (?, ?, ?)
            ON CONFLICT(asset_id, tag_key) DO UPDATE SET
                tag_value = excluded.tag_value,
                added_at = CURRENT_TIMESTAMP
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (asset_id, key, value))
            conn.commit()
            logger.info(f"Tagged asset {asset_id} with {key}={value}")

    def get_tags(self, asset_id: int) -> Dict[str, str]:
        """Retrieves all tags for a specific asset."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT tag_key, tag_value FROM asset_tags WHERE asset_id = ?", (asset_id,))
            rows = cursor.fetchall()
            return {row["tag_key"]: row["tag_value"] for row in rows}

    def get_assets_by_tag(self, key: str, value: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all data assets that match a specific tag key and optional value."""
        if value:
            query = """
                SELECT a.* FROM data_assets a
                JOIN asset_tags t ON a.asset_id = t.asset_id
                WHERE t.tag_key = ? AND t.tag_value = ?
            """
            params = (key, value)
        else:
            query = """
                SELECT a.* FROM data_assets a
                JOIN asset_tags t ON a.asset_id = t.asset_id
                WHERE t.tag_key = ?
            """
            params = (key,)

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_schema_hierarchy(self) -> Dict[str, Any]:
        """
        Builds and returns the nested schema tree:
        Database -> Schema -> Table -> Columns
        """
        hierarchy: Dict[str, Any] = {}
        assets = self.catalog.list_all_assets()
        
        for asset in assets:
            db = asset["database_name"]
            schema = asset["schema_name"]
            table = asset["table_name"]
            col = asset["column_name"]
            dtype = asset["data_type"]
            sens = asset["sensitivity_level"]
            
            if db not in hierarchy:
                hierarchy[db] = {}
            if schema not in hierarchy[db]:
                hierarchy[db][schema] = {}
            if table not in hierarchy[db][schema]:
                hierarchy[db][schema][table] = []
                
            hierarchy[db][schema][table].append({
                "column_name": col,
                "data_type": dtype,
                "sensitivity_level": sens,
                "owner": asset["owner"]
            })
            
        return hierarchy
