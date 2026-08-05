"""Secrets management: AWS Secrets Manager, Azure Key Vault, Vault, env."""
from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import Any
from shared.exceptions import SecretError

class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, name: str) -> str: ...

class EnvSecretProvider(SecretProvider):
    def __init__(self, prefix=""): self.prefix=prefix
    def get_secret(self, name):
        k=f"{self.prefix}{name}" if self.prefix else name
        v=os.environ.get(k)
        if v is None: raise SecretError(f"Secret '{name}' not found")
        return v

class InMemorySecretProvider(SecretProvider):
    def __init__(self, secrets=None): self._s=secrets or {}
    def set_secret(self, n, v): self._s[n]=v
    def get_secret(self, n):
        if n not in self._s: raise SecretError(f"Secret '{n}' not found")
        return self._s[n]

class SecretsManager:
    def __init__(self): self._providers=[]; self._cache={}
    def add_provider(self, p): self._providers.append(p)
    def get_secret(self, name, use_cache=True):
        if use_cache and name in self._cache: return self._cache[name]
        for p in self._providers:
            try:
                v=p.get_secret(name); self._cache[name]=v; return v
            except SecretError: continue
        raise SecretError(f"Secret '{name}' not found")
    def clear_cache(self): self._cache.clear()

