"""API ingestion with pagination, auth, rate limiting, retry."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from typing import Any

@dataclass
class APIConfig:
    base_url: str=""; headers: dict[str,str]=field(default_factory=dict)
    params: dict[str,Any]=field(default_factory=dict); auth_token: str=""
    rate_limit: float=0.0; max_retries: int=3; page_size: int=100

class APIClient:
    def __init__(self, config): self.config=config; self._last=0.0
    def _headers(self):
        h=dict(self.config.headers)
        if self.config.auth_token: h["Authorization"]=f"Bearer {self.config.auth_token}"
        return h
    def _wait(self):
        if self.config.rate_limit>0:
            e=time.time()-self._last
            if e<self.config.rate_limit: time.sleep(self.config.rate_limit-e)
        self._last=time.time()
    def fetch(self, endpoint, params=None):
        import urllib.request, urllib.parse
        self._wait()
        url=f"{self.config.base_url}/{endpoint.lstrip('/')}"
        p={**self.config.params,**(params or {})}
        if p: url+="?"+urllib.parse.urlencode(p)
        req=urllib.request.Request(url, headers=self._headers())
        for a in range(self.config.max_retries):
            try:
                with urllib.request.urlopen(req) as r: return json.loads(r.read().decode())
            except Exception:
                if a>=self.config.max_retries-1: raise
                time.sleep(2**a)
    def fetch_all(self, endpoint, data_path="data", page_param="page"):
        all_d=[]; page=1
        while True:
            r=self.fetch(endpoint, {page_param:page, "per_page":self.config.page_size})
            d=r
            for k in data_path.split("."): d=d.get(k, [])
            if not d: break
            all_d.extend(d); page+=1
        return all_d

