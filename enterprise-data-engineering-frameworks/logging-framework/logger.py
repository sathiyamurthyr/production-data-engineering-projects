"""Structured logging with correlation IDs and JSON output."""
from __future__ import annotations
import json, logging, sys
from contextvars import ContextVar
from typing import Any

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

class StructuredLogger:
    def __init__(self, name, level="INFO", json_output=False):
        self.name=name; self.json_output=json_output
        self._logger=logging.getLogger(name)
        self._logger.setLevel(getattr(logging,level.upper(),logging.INFO))
        if not self._logger.handlers:
            h=logging.StreamHandler(sys.stdout); h.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(h)
    def _log(self, level, msg, **kw):
        entry={"logger":self.name,"level":level,"message":msg,"correlation_id":correlation_id_var.get(),**kw}
        if self.json_output: out=json.dumps(entry,default=str)
        else: out=f"[{level}] {self.name}: {msg}"; 
        if kw and not self.json_output: out+=f" {json.dumps(kw,default=str)}"
        self._logger.log(getattr(logging,level,logging.INFO),out)
    def debug(self,m,**kw): self._log("DEBUG",m,**kw)
    def info(self,m,**kw): self._log("INFO",m,**kw)
    def warning(self,m,**kw): self._log("WARNING",m,**kw)
    def error(self,m,**kw): self._log("ERROR",m,**kw)

def set_correlation_id(cid): correlation_id_var.set(cid)
def get_logger(name, **kw): return StructuredLogger(name, **kw)

