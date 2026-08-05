"""Plugin architecture with registration, lifecycle, and discovery."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from shared.exceptions import PluginError

class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def version(self) -> str: ...
    @abstractmethod
    def initialize(self, context: dict[str, Any]) -> None: ...
    @abstractmethod
    def shutdown(self) -> None: ...
    def on_register(self) -> None: ...
    def on_unregister(self) -> None: ...

@dataclass
class PluginInfo:
    name: str
    version: str
    instance: Plugin
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

class PluginManager:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}
        self._hooks: dict[str, list] = {}
    def register(self, plugin: Plugin, config: dict | None = None) -> None:
        if plugin.name in self._plugins:
            raise PluginError(f"Plugin '{plugin.name}' is already registered")
        self._plugins[plugin.name] = PluginInfo(name=plugin.name, version=plugin.version, instance=plugin, config=config or {})
        plugin.on_register()
    def unregister(self, name: str) -> None:
        if name not in self._plugins:
            raise PluginError(f"Plugin '{name}' is not registered")
        info = self._plugins.pop(name)
        if info.enabled: info.instance.shutdown()
        info.instance.on_unregister()
    def get(self, name: str) -> Plugin | None:
        info = self._plugins.get(name)
        return info.instance if info and info.enabled else None
    def list_plugins(self) -> list[PluginInfo]:
        return list(self._plugins.values())
    def enable(self, name: str) -> None:
        if name in self._plugins:
            self._plugins[name].enabled = True
            self._plugins[name].instance.initialize(self._plugins[name].config)
    def disable(self, name: str) -> None:
        if name in self._plugins:
            self._plugins[name].enabled = False
            self._plugins[name].instance.shutdown()
    def initialize_all(self, context: dict[str, Any]) -> None:
        for info in self._plugins.values():
            if info.enabled: info.instance.initialize({**context, **info.config})
    def shutdown_all(self) -> None:
        for info in self._plugins.values():
            if info.enabled: info.instance.shutdown()
    def register_hook(self, hook_name: str, callback) -> None:
        self._hooks.setdefault(hook_name, []).append(callback)
    def execute_hooks(self, hook_name: str, *args, **kwargs) -> list:
        return [cb(*args, **kwargs) for cb in self._hooks.get(hook_name, [])]

