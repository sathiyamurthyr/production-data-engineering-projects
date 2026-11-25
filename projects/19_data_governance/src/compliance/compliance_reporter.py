"""
Compliance Reporter Module
==========================
Aggregates compliance audit results, computes organizational governance scores,
and identifies security vulnerabilities or regulatory violations.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any
from src.catalog.data_catalog import DataCatalog
from src.access_control.audit_logger import AuditLogger
from src.compliance.data_retention import DataRetentionManager

logger = logging.getLogger(__name__)

@dataclass
class ComplianceSummary:
    """Summary of enterprise compliance posture."""
    total_assets: int
    pii_asset_count: int
    unmasked_pii_access_count: int
    unauthorized_attempt_count: int
    retention_violations_count: int
    compliance_score: float  # 0.0 to 100.0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    risk_level: str = "LOW"
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert compliance summary to dictionary."""
        return asdict(self)


class ComplianceReporter:
    """
    Generates multi-regulation compliance and risk reports.
    """

    def __init__(
        self,
        catalog: DataCatalog,
        audit_logger: AuditLogger,
        retention_manager: DataRetentionManager,
    ) -> None:
        self.catalog = catalog
        self.audit_logger = audit_logger
        self.retention_manager = retention_manager

    def generate_summary_report(self) -> ComplianceSummary:
        """
        Compile governance metrics and compute an overall compliance health score.
        
        Returns:
            ComplianceSummary dataclass instance.
        """
        all_assets = self.catalog.list_all()
        total_assets = len(all_assets)
        pii_assets = [a for a in all_assets if a.sensitivity_level in ("CONFIDENTIAL", "RESTRICTED")]

        # Audit events
        unauthorized = self.audit_logger.get_unauthorized_attempts()
        all_events = self.audit_logger._events
        unmasked_access = [e for e in all_events if e.details.get("unmasked", False)]

        # Retention checks
        asset_dicts = [{"asset_id": a.asset_id, "domain": a.domain, "created_date": a.created_at} for a in all_assets]
        retention_actions = self.retention_manager.evaluate_all_assets(asset_dicts)
        violations = [r for r in retention_actions if r.action_required != "NONE"]

        # Calculate Compliance Score (Base 100)
        score = 100.0
        score -= min(30.0, len(unauthorized) * 5.0)
        score -= min(30.0, len(violations) * 10.0)
        if total_assets > 0 and (len(pii_assets) / total_assets) > 0.5 and len(unmasked_access) > 5:
            score -= 15.0

        score = max(0.0, round(score, 1))

        if score >= 85.0:
            risk = "LOW"
        elif score >= 60.0:
            risk = "MEDIUM"
        else:
            risk = "HIGH"

        recommendations = []
        if len(unauthorized) > 0:
            recommendations.append(f"Investigate {len(unauthorized)} unauthorized access attempts logged.")
        if len(violations) > 0:
            recommendations.append(f"Enforce lifecycle purge/archive on {len(violations)} expired datasets.")
        if len(pii_assets) > 0:
            recommendations.append(f"Verify encryption and masking policies for {len(pii_assets)} restricted PII assets.")

        summary = ComplianceSummary(
            total_assets=total_assets,
            pii_asset_count=len(pii_assets),
            unmasked_pii_access_count=len(unmasked_access),
            unauthorized_attempt_count=len(unauthorized),
            retention_violations_count=len(violations),
            compliance_score=score,
            risk_level=risk,
            recommendations=recommendations,
        )

        logger.info(f"Compliance report generated: score={score}, risk={risk}.")
        return summary

    def export_json(self) -> str:
        """Export compliance summary report as formatted JSON."""
        summary = self.generate_summary_report()
        return json.dumps(summary.to_dict(), indent=2)
