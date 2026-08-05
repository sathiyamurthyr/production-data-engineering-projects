"""Dependency injection container."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from shared.exceptions import ConfigurationError

class Scope(Enum):
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"

@dataclass
class Registration:
    interface: type
    implementation: type | Any
    scope: Scope = Scope.SINGLETON
    factory: Any | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)

class Container:
    def __init__(self) -> None:
        self._registrations: dict[type, Registration] = {}
        self._singletons: dict[type, Any] = {}
        self._resolving: set[type] = set()
    def register(self, interface: type, implementation: type | Any = None, scope: Scope = Scope.SINGLETON, **kwargs: Any) -> None:
        self._registrations[interface] = Registration(interface=interface, implementation=implementation or interface, scope=scope, kwargs=kwargs)
    def register_factory(self, interface: type, factory: Any, scope: Scope = Scope.TRANSIENT) -> None:
        self._registrations[interface] = Registration(interface=interface, implementation=factory, scope=scope, factory=factory)
    def register_instance(self, interface: type, instance: Any) -> None:
        self._registrations[interface] = Registration(interface=interface, implementation=type(instance), scope=Scope.SINGLETON)
        self._singletons[interface] = instance
    def resolve(self, interface: type) -> Any:
        if interface not in self._registrations:
            raise ConfigurationError(f"No registration for {interface.__name__}")
        if interface in self._resolving:
            raise ConfigurationError(f"Circular dependency detected for {interface.__name__}")
        reg = self._registrations[interface]
        if reg.scope == Scope.SINGLETON and interface in self._singletons:
            return self._singletons[interface]
        self._resolving.add(interface)
        try:
            instance = reg.factory(self) if reg.factory else reg.implementation(**reg.kwargs)
        finally:
            self._resolving.discard(interface)
        if reg.scope == Scope.SINGLETON:
            self._singletons[interface] = instance
        return instance

