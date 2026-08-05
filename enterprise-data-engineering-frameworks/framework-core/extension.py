"""Extension SDK for building custom framework extensions."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ExtensionManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)

class Extension(ABC):
    @property
    @abstractmethod
    def manifest(self) -> ExtensionManifest: ...
    @abstractmethod
    def install(self, context: dict[str, Any]) -> None: ...
    @abstractmethod
    def uninstall(self) -> None: ...
    def configure(self, config: dict[str, Any]) -> None:
        self._config = config

class ExtensionManager:
    def __init__(self) -> None:
        self._extensions: dict[str, Extension] = {}
        self._manifests: dict[str, ExtensionManifest] = {}
    def install(self, extension: Extension, config: dict | None = None) -> None:
        manifest = extension.manifest
        if manifest.name in self._extensions:
            raise ValueError(f"Extension '{manifest.name}' already installed")
        for dep in manifest.dependencies:
            if dep not in self._extensions:
                raise ValueError(f"Missing dependency: {dep}")
        if config:
            extension.configure(config)
        extension.install({"manager": self})
        self._extensions[manifest.name] = extension
        self._manifests[manifest.name] = manifest
    def uninstall(self, name: str) -> None:
        if name not in self._extensions:
            raise ValueError(f"Extension '{name}' not installed")
        self._extensions[name].uninstall()
        del self._extensions[name]
        del self._manifests[name]
    def get(self, name: str) -> Extension | None:
        return self._extensions.get(name)
    def list_extensions(self) -> list[ExtensionManifest]:
        return list(self._manifests.values())

