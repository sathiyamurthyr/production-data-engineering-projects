"""
Sensitivity Tagger Module
=========================
Applies governance classifications and sensitivity tags to data catalog assets.
"""

import sqlite3
import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from src.catalog.data_catalog import DataCatalog
from src.classification.data_classifier import ClassificationResult

logger = logging.getLogger(__name__)

@dataclass
class TagResult:
    """Represents a successfully applied sensitivity tag record."""
    target_identifier: str
    sensitivity_level: str
    applied_by: str = "automated_classifier"
    reason: str = ""


class SensitivityTagger:
    """
    Applies security/sensitivity levels to catalog assets and keeps audit records of manual or automated modifications.
    """
    def __init__(self, catalog: Optional[DataCatalog] = None):
        self.catalog = catalog or DataCatalog()
        self._init_audit_table()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.catalog.db_path)

    def _init_audit_table(self):
        """Initializes the sensitivity levels audit log table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensitivity_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    old_sensitivity TEXT NOT NULL,
                    new_sensitivity TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    reason TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(asset_id) REFERENCES data_assets(asset_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sens_audit_asset ON sensitivity_audit(asset_id)")
            conn.commit()

    def tag_sensitivity(self, asset_id: int, new_level: str, changed_by: str, reason: str) -> bool:
        """
        Updates the sensitivity level of an asset and logs it to the audit table.
        
        Args:
            asset_id: The ID of the asset.
            new_level: The new sensitivity level.
            changed_by: The user or pipeline name triggering this change.
            reason: Explanation of the change.
            
        Returns:
            True if successfully updated, False otherwise.
        """
        asset = self.catalog.get_asset_by_id(asset_id)
        if not asset:
            logger.error(f"Cannot tag sensitivity: Asset ID {asset_id} does not exist.")
            return False

        old_level = asset["sensitivity_level"]
        
        # Avoid duplicate audit entries if nothing changed
        if old_level == new_level:
            return True

        # 1. Update Catalog
        self.catalog.update_sensitivity(asset_id, new_level)
        
        # 2. Write Audit Log
        query = """
            INSERT INTO sensitivity_audit (asset_id, old_sensitivity, new_sensitivity, changed_by, reason)
            VALUES (?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (asset_id, old_level, new_level, changed_by, reason))
            conn.commit()
            
        logger.info(f"Updated Asset ID {asset_id} sensitivity from '{old_level}' to '{new_level}' by {changed_by}")
        return True

    def tag_classification_result(self, target_identifier: str, result: ClassificationResult) -> List[TagResult]:
        """
        Applies classification result to target identifier and returns corresponding TagResults.
        """
        logger.info(f"Tagging classification results on '{target_identifier}'")
        
        tag_result = TagResult(
            target_identifier=target_identifier,
            sensitivity_level=result.overall_sensitivity,
            applied_by="automated_classifier",
            reason=f"Scanned {result.pii_column_count} PII fields in dataset '{result.dataset_name}'"
        )
        
        # Attempt to apply to catalog entry if applicable
        if self.catalog:
            try:
                # If target identifier exists as a string asset_id in catalog_entries
                self.catalog.update_sensitivity(target_identifier, result.overall_sensitivity)
            except Exception as e:
                logger.warning(f"Could not apply catalog update for '{target_identifier}': {e}")
                
        return [tag_result]

    def get_sensitivity_history(self, asset_id: int) -> List[Dict[str, Any]]:
        """Retrieves audit trail of sensitivity changes for a specific asset."""
        query = """
            SELECT * FROM sensitivity_audit 
            WHERE asset_id = ? 
            ORDER BY changed_at DESC
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (asset_id,))
            return [dict(row) for row in cursor.fetchall()]
