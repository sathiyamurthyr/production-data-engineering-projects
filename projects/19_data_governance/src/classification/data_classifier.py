"""
Data Classifier Module
======================
Automates the classification of datasets and columns by detecting PII and tagging sensitivity level.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from src.catalog.data_catalog import DataCatalog
from src.classification.pii_detector import PIIDetector

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Holds results of dataset classification scanning."""
    dataset_name: str
    column_classifications: Dict[str, str]
    overall_sensitivity: str
    pii_column_count: int


class DataClassifier:
    """
    Orchestrates the automated scanning of datasets, runs PII detection, 
    and returns classification results.
    """
    def __init__(self, catalog: Optional[DataCatalog] = None, config_path: str = "configs/governance_config.yaml"):
        # Make catalog optional for testing convenience
        self.catalog = catalog or DataCatalog()
        self.detector = PIIDetector(config_path)

    def classify_dataset(self, dataset_name: str, dataset_data: Dict[str, List[Any]]) -> ClassificationResult:
        """
        Scans a dictionary mapping column names to lists of values and returns classification results.
        
        Args:
            dataset_name: Name of the dataset/table.
            dataset_data: Dict of column_name -> list of column values.
            
        Returns:
            ClassificationResult summary.
        """
        logger.info(f"Classifying dataset '{dataset_name}' with {len(dataset_data)} columns")
        col_classifications = {}
        pii_count = 0
        
        for col, values in dataset_data.items():
            label, score = self.detector.scan_column(values)
            col_classifications[col] = label
            if label != "PUBLIC":
                pii_count += 1
                
        # Determine overall sensitivity (highest grade wins: RESTRICTED > CONFIDENTIAL > PUBLIC)
        overall = "PUBLIC"
        labels = set(col_classifications.values())
        if "RESTRICTED" in labels:
            overall = "RESTRICTED"
        elif "CONFIDENTIAL" in labels:
            overall = "CONFIDENTIAL"
        elif "INTERNAL" in labels:
            overall = "INTERNAL"
            
        return ClassificationResult(
            dataset_name=dataset_name,
            column_classifications=col_classifications,
            overall_sensitivity=overall,
            pii_column_count=pii_count
        )

    def classify_and_tag_dataframe(self, df: Any, database_name: str, schema_name: str, table_name: str, trigger_by: str = "automated_classifier") -> Dict[str, str]:
        """
        Scans a Pandas DataFrame or dict-like object, writes column catalog schemas, 
        and updates sensitivity levels in the catalog.
        
        Args:
            df: Pandas DataFrame or data dict.
            database_name: Catalog database target.
            schema_name: Catalog schema target.
            table_name: Catalog table target.
            trigger_by: Event source identifier.
            
        Returns:
            A dictionary mapping column name to its applied classification.
        """
        # Convert DataFrame/dict columns to Dict[str, list]
        dataset_data = {}
        columns = getattr(df, "columns", [])
        if not columns and hasattr(df, "keys"):
            columns = df.keys()
            
        for col_name in columns:
            if hasattr(df, "getitem") or (hasattr(df, "__getitem__") and not isinstance(df, dict)):
                values = df[col_name].tolist() if hasattr(df[col_name], "tolist") else list(df[col_name])
            else:
                values = df.get(col_name, [])
            dataset_data[col_name] = values
            
        res = self.classify_dataset(table_name, dataset_data)
        
        # Register assets and tag them
        from src.classification.sensitivity_tagger import SensitivityTagger
        tagger = SensitivityTagger(self.catalog)
        
        for col_name, classification in res.column_classifications.items():
            asset = self.catalog.get_asset_by_path(database_name, schema_name, table_name, col_name)
            if not asset:
                # Register column dynamically if missing
                inferred_type = "VARCHAR"
                values = dataset_data.get(col_name, [])
                if values:
                    inferred_type = type(values[0]).__name__.upper()
                
                asset_id = self.catalog.register_asset({
                    "database_name": database_name,
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "column_name": col_name,
                    "data_type": inferred_type,
                    "description": "Auto-registered during classification",
                    "owner": "UNKNOWN",
                    "business_domain": "general",
                    "sensitivity_level": classification
                })
            else:
                asset_id = asset["asset_id"]
                
            reason = f"Automated classification scan detected {classification}"
            tagger.tag_sensitivity(asset_id, classification, trigger_by, reason)
            
        return res.column_classifications
