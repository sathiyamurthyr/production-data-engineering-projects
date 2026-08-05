"""Storage abstraction for file, object, and database storage."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

class StorageBackend(ABC):
    @abstractmethod
    def read(self, path: str) -> bytes: ...
    @abstractmethod
    def write(self, path: str, data: bytes) -> None: ...
    @abstractmethod
    def exists(self, path: str) -> bool: ...
    @abstractmethod
    def delete(self, path: str) -> None: ...
    @abstractmethod
    def list(self, prefix: str) -> list[str]: ...

class LocalStorage(StorageBackend):
    def __init__(self, base_path: str | Path = ".") -> None:
        self.base_path = Path(base_path)
    def read(self, path: str) -> bytes:
        return (self.base_path / path).read_bytes()
    def write(self, path: str, data: bytes) -> None:
        full = self.base_path / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
    def exists(self, path: str) -> bool:
        return (self.base_path / path).exists()
    def delete(self, path: str) -> None:
        (self.base_path / path).unlink()
    def list(self, prefix: str) -> list[str]:
        base = self.base_path / prefix
        if base.is_dir():
            return [str(p.relative_to(self.base_path)) for p in base.rglob("*") if p.is_file()]
        return []

class InMemoryStorage(StorageBackend):
    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}
    def read(self, path: str) -> bytes:
        return self._data[path]
    def write(self, path: str, data: bytes) -> None:
        self._data[path] = data
    def exists(self, path: str) -> bool:
        return path in self._data
    def delete(self, path: str) -> None:
        self._data.pop(path, None)
    def list(self, prefix: str) -> list[str]:
        return [p for p in self._data if p.startswith(prefix)]

class StorageManager:
    def __init__(self) -> None:
        self._backends: dict[str, StorageBackend] = {}
        self.register("file", LocalStorage())
        self.register("memory", InMemoryStorage())
    def register(self, scheme: str, backend: StorageBackend) -> None:
        self._backends[scheme] = backend
    def get_backend(self, uri: str) -> StorageBackend:
        scheme = uri.split("://")[0] if "://" in uri else "file"
        if scheme not in self._backends:
            raise ValueError(f"Unknown storage scheme: {scheme}")
        return self._backends[scheme]
    def read(self, uri: str) -> bytes:
        backend = self.get_backend(uri)
        path = uri.split("://", 1)[1] if "://" in uri else uri
        return backend.read(path)
    def write(self, uri: str, data: bytes) -> None:
        backend = self.get_backend(uri)
        path = uri.split("://", 1)[1] if "://" in uri else uri
        backend.write(path, data)

