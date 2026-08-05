"""Multi-channel notifications: email, Slack, Teams, PagerDuty, webhooks."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import generate_id, utc_now_iso

@dataclass
class Notification:
    id: str=field(default_factory=lambda: generate_id("notif_"))
    channel: str=""; subject: str=""; body: str=""
    recipients: list[str]=field(default_factory=list); priority: str="normal"
    timestamp: str=field(default_factory=utc_now_iso)

class NotificationChannel(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def send(self, n: Notification) -> bool: ...

class ConsoleChannel(NotificationChannel):
    @property
    def name(self): return "console"
    def send(self, n): print(f"[{n.channel}] {n.subject}: {n.body}"); return True

class NotificationEngine:
    def __init__(self): self._channels={}; self._history=[]
    def register(self, name, ch): self._channels[name]=ch
    def send(self, channel, subject, body, recipients=None, priority="normal"):
        if channel not in self._channels: return False
        n=Notification(channel=channel,subject=subject,body=body,recipients=recipients or [],priority=priority)
        r=self._channels[channel].send(n)
        if r: self._history.append(n)
        return r
    def broadcast(self, subject, body, **kw): return {n:self.send(n,subject,body,**kw) for n in self._channels}
    def get_history(self): return list(self._history)

