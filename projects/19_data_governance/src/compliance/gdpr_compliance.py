"""
GDPR & Data Privacy Compliance Module
====================================
Implements regulatory compliance operations including Subject Access Requests (SAR),
Right to be Forgotten (RTBF) erasure workflows, and consent validation.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.catalog.data_catalog import DataCatalog

logger = logging.getLogger(__name__)

@dataclass
class SARReport:
    """Subject Access Request (SAR) compilation report for a data subject."""
    subject_id: str
    request_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    retrieved_records: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    total_records_found: int = 0
    status: str = "COMPLETED"

    def to_dict(self) -> Dict[str, Any]:
        """Convert SAR report to dictionary."""
        return asdict(self)


@dataclass
class ErasureReport:
    """Right to Be Forgotten (RTBF) deletion execution report."""
    subject_id: str
    erasure_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    affected_datasets: List[str] = field(default_factory=list)
    records_erased_count: int = 0
    records_anonymized_count: int = 0
    status: str = "COMPLETED"

    def to_dict(self) -> Dict[str, Any]:
        """Convert Erasure report to dictionary."""
        return asdict(self)


class GDPRComplianceChecker:
    """
    Executes GDPR regulatory processes against cataloged data stores.
    """

    def __init__(self, catalog: DataCatalog) -> None:
        self.catalog = catalog

    def process_subject_access_request(
        self,
        subject_id: str,
        datasets: Dict[str, List[Dict[str, Any]]],
        id_column_name: str = "customer_id",
    ) -> SARReport:
        """
        Extract all records associated with a data subject across provided datasets.
        
        Args:
            subject_id: Data subject identifier (e.g. CUST_1001).
            datasets: Dict mapping dataset_name -> list of row dicts.
            id_column_name: Primary subject key field.
            
        Returns:
            SARReport containing all collected data.
        """
        found_data: Dict[str, List[Dict[str, Any]]] = {}
        total_found = 0

        for dataset_name, rows in datasets.items():
            matching_rows = [
                row for row in rows
                if str(row.get(id_column_name, "")).strip().lower() == str(subject_id).strip().lower()
            ]
            if matching_rows:
                found_data[dataset_name] = matching_rows
                total_found += len(matching_rows)

        report = SARReport(
            subject_id=subject_id,
            retrieved_records=found_data,
            total_records_found=total_found,
            status="COMPLETED",
        )
        logger.info(f"SAR completed for subject '{subject_id}': found {total_found} records across {len(found_data)} datasets.")
        return report

    def process_right_to_be_forgotten(
        self,
        subject_id: str,
        datasets: Dict[str, List[Dict[str, Any]]],
        id_column_name: str = "customer_id",
        anonymize_fields: Optional[List[str]] = None,
    ) -> ErasureReport:
        """
        Purge or anonymize records for a data subject across datasets.
        
        Args:
            subject_id: Data subject identifier.
            datasets: Mutable dict mapping dataset_name -> list of row dicts.
            id_column_name: Subject key field.
            anonymize_fields: Optional list of fields to anonymize instead of full row purge.
            
        Returns:
            ErasureReport summarizing deleted/anonymized records.
        """
        affected: List[str] = []
        erased_count = 0
        anonymized_count = 0

        for dataset_name, rows in datasets.items():
            initial_count = len(rows)
            if anonymize_fields:
                for row in rows:
                    if str(row.get(id_column_name, "")).strip().lower() == str(subject_id).strip().lower():
                        for f in anonymize_fields:
                            if f in row:
                                row[f] = "[ANONYMIZED]"
                        anonymized_count += 1
                        if dataset_name not in affected:
                            affected.append(dataset_name)
            else:
                # Full row deletion
                retained_rows = [
                    row for row in rows
                    if str(row.get(id_column_name, "")).strip().lower() != str(subject_id).strip().lower()
                ]
                deleted = initial_count - len(retained_rows)
                if deleted > 0:
                    datasets[dataset_name] = retained_rows
                    erased_count += deleted
                    affected.append(dataset_name)

        report = ErasureReport(
            subject_id=subject_id,
            affected_datasets=affected,
            records_erased_count=erased_count,
            records_anonymized_count=anonymized_count,
            status="COMPLETED",
        )
        logger.info(f"RTBF executed for subject '{subject_id}': erased={erased_count}, anonymized={anonymized_count}.")
        return report
