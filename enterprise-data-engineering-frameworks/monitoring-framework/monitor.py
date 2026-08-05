"""Monitoring: pipeline monitoring, metrics, health checks, alerting."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import utc_now_iso

@dataclass
class HealthCheck:
    name: str; check_fn: Any; interval: float=60.0

@dataclass
class HealthStatus:
    name: str; healthy: bool; message: str=""; timestamp: str=field(default_factory=utc_now_iso)

@dataclass
class Alert:
    alert_id: str=field(default_factory=lambda: f"alert_{utc_now_iso()}")
    name: str=""; severity: str="warning"; message: str=""
    timestamp: str=field(default_factory=utc_now_iso); acknowledged: bool=False

class MonitoringEngine:
    def __init__(self): self._checks={}; self._alerts=[]; self._metrics={}
    def add_health_check(self, c): self._checks[c.name]=c
    def run_health_checks(self):
        r=[]
        for n,c in self._checks.items():
            try: r.append(HealthStatus(n, bool(c.check_fn())))
            except Exception as e: r.append(HealthStatus(n, False, str(e)))
        return r
    def set_metric(self, n, v): self._metrics[n]=v
    def get_metric(self, n): return self._metrics.get(n)
    def raise_alert(self, name, severity="warning", message=""):
        a=Alert(name=name,severity=severity,message=message); self._alerts.append(a); return a
    def acknowledge_alert(self, aid):
        for a in self._alerts:
            if a.alert_id==aid: a.acknowledged=True; break
    def get_alerts(self, unack_only=False):
        if unack_only: return [a for a in self._alerts if not a.acknowledged]
        return list(self._alerts)

