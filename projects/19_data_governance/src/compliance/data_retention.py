"""
Data Retention Lifecycle Module
===============================
Enforces corporate data lifecycle policies, computing record ages and triggering
automated purge, archiving, or locking actions based on retention schedules.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class RetentionPolicy:
    """Defines retention lifecycle rules for a domain or dataset."""
    domain: str
    retention_days: int
    action: str  # "PURGE", "ARCHIVE", "LOCK_AND_ARCHIVE"
    policy_name: str = ""


@dataclass
class RetentionAction:
    """Result of a retention rule evaluation."""
    asset_id: str
    domain: str
    age_days: int
    max_retention_days: int
    action_required: str  # "NONE", "PURGE", "ARCHIVE", "LOCK_AND_ARCHIVE"
    status: str = "EVALUATED"

    def to_dict(self) -> Dict[str, Any]:
        """Convert retention action to dictionary."""
        return asdict(self)


class DataRetentionManager:
    """
    Evaluates dataset age against corporate retention matrices and executes lifecycle policies.
    """

    def __init__(self) -> None:
        self._policies: Dict[str, RetentionPolicy] = {}
        self._init_default_policies()

    def _init_default_policies(self) -> None:
        """Set standard enterprise retention rules."""
        self.add_policy(RetentionPolicy("customer_360", 1825, "ARCHIVE", "POL_CUST_5YR"))
        self.add_policy(RetentionPolicy("finance", 2555, "LOCK_AND_ARCHIVE", "POL_FIN_7YR"))
        self.add_policy(RetentionPolicy("marketing", 365, "PURGE", "POL_MKTG_1YR"))
        self.add_policy(RetentionPolicy("logs", 90, "PURGE", "POL_LOGS_90D"))

    def add_policy(self, policy: RetentionPolicy) -> None:
        """Register or update a retention policy for a domain."""
        if not policy.policy_name:
            policy.policy_name = f"POL_{policy.domain.upper()}"
        self._policies[policy.domain] = policy
        logger.info(f"Registered retention policy '{policy.policy_name}' for domain '{policy.domain}': {policy.retention_days} days -> {policy.action}.")

    def evaluate_asset_age(self, asset_id: str, created_date_str: str, domain: str) -> RetentionAction:
        """
        Evaluate whether an asset has breached its domain retention limit.
        
        Args:
            asset_id: Asset identifier.
            created_date_str: ISO format date string (e.g. YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ).
            domain: Business domain.
            
        Returns:
            RetentionAction object.
        """
        policy = self._policies.get(domain)
        if not policy:
            # Default safety policy: retain for 365 days, archive
            policy = RetentionPolicy(domain, 365, "ARCHIVE", "POL_DEFAULT")

        try:
            clean_date = created_date_str.replace("Z", "").split("T")[0]
            created_dt = datetime.fromisoformat(clean_date)
        except ValueError:
            created_dt = datetime.utcnow()

        age_days = (datetime.utcnow() - created_dt).days

        if age_days >= policy.retention_days:
            action_req = policy.action
        else:
            action_req = "NONE"

        action = RetentionAction(
            asset_id=asset_id,
            domain=domain,
            age_days=age_days,
            max_retention_days=policy.retention_days,
            action_required=action_req,
        )

        logger.info(f"Retention evaluation for asset '{asset_id}' (age={age_days}d): action={action_req}.")
        return action

    def evaluate_all_assets(self, assets: List[Dict[str, Any]]) -> List[RetentionAction]:
        """Bulk evaluate retention policies across a list of asset dicts."""
        actions: List[RetentionAction] = []
        for a in assets:
            action = self.evaluate_asset_age(
                asset_id=a["asset_id"],
                created_date_str=a.get("created_date", datetime.utcnow().isoformat()),
                domain=a.get("domain", "general"),
            )
            actions.append(action)
        return actions
