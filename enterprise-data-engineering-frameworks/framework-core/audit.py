"""Audit engine for recording audit trails."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from shared.utils.helpers import generate_id, utc_now_iso

@dataclass
class AuditEvent:
    event_id: str = field(default_factory=lambda: generate_id("audit_"))
    event_type: str = ""
    actor: str = ""
    action: str = ""
    resource: str = ""
    timestamp: str = field(default_factory=utc_now_iso)
    details: dict[str, Any] = field(default_factory=dict)
    outcome: str = "success"

class AuditEngine:
    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = Path(store_path) if store_path else None
        self._events: list[AuditEvent] = []
        self._backends: list = []
    def record(self, event_type: str, actor: str, action: str, resource: str = "", details: dict | None = None, outcome: str = "success") -> AuditEvent:
        event = AuditEvent(event_type=event_type, actor=actor, action=action, resource=resource, details=details or {}, outcome=outcome)
        self._events.append(event)
        self._persist(event)
        for backend in self._backends:
            backend(event)
        return event
    def add_backend(self, backend) -> None:
        self._backends.append(backend)
    def query(self, event_type: str | None = None, actor: str | None = None, action: str | None = None, resource: str | None = None) -> list[AuditEvent]:
        results = self._events
        if event_type: results = [e for e in results if e.event_type == event_type]
        if actor: results = [e for e in results if e.actor == actor]
        if action: results = [e for e in results if e.action == action]
        if resource: results = [e for e in results if e.resource == resource]
        return results
    def export(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps([asdict(e) for e in self._events], indent=2, default=str))
    def _persist(self, event: AuditEvent) -> None:
        if self._store_path:
            with self._store_path.open("a") as f:
                f.write(json.dumps(asdict(event), default=str) + "\n")

