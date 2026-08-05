"""Data governance: policies, access control, compliance, audit, retention."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from shared.utils.helpers import utc_now_iso

class AccessLevel(Enum):
    READ="read"; WRITE="write"; ADMIN="admin"

@dataclass
class AccessPolicy:
    name: str; resource: str; principal: str; access: AccessLevel=AccessLevel.READ
    conditions: list=field(default_factory=list)

@dataclass
class RetentionPolicy:
    name: str; table: str; retention_days: int=365; action: str="delete"

class GovernanceEngine:
    def __init__(self): self._policies=[]; self._retention=[]; self._audit=[]
    def add_access_policy(self, p): self._policies.append(p)
    def check_access(self, principal, resource, access, context=None):
        ctx=context or {}
        for p in self._policies:
            if p.principal==principal and p.resource==resource:
                if p.access==access or (p.access==AccessLevel.ADMIN and access in [AccessLevel.READ,AccessLevel.WRITE]):
                    if all(c(ctx) for c in p.conditions): return True
        return False
    def add_retention_policy(self, p): self._retention.append(p)
    def get_retention(self, table):
        return next((r for r in self._retention if r.table==table), None)
    def audit(self, action, principal, resource, outcome="success"):
        self._audit.append({"action":action,"principal":principal,"resource":resource,"outcome":outcome,"timestamp":utc_now_iso()})
    def get_audit_trail(self): return list(self._audit)

