"""Validation engine for data and configuration validation."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from shared.exceptions import ValidationError

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

class Validator(ABC):
    @abstractmethod
    def validate(self, data: Any) -> ValidationResult: ...

class SchemaValidator(Validator):
    def __init__(self, schema: dict[str, type]) -> None:
        self.schema = schema
    def validate(self, data: Any) -> ValidationResult:
        errors = []
        if not isinstance(data, dict):
            return ValidationResult(is_valid=False, errors=["Data must be a dictionary"])
        for field_name, field_type in self.schema.items():
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")
            elif not isinstance(data[field_name], field_type):
                errors.append(f"Field '{field_name}' wrong type")
        return ValidationResult(is_valid=len(errors)==0, errors=errors)

class RangeValidator(Validator):
    def __init__(self, min_val: float | None = None, max_val: float | None = None) -> None:
        self.min_val = min_val
        self.max_val = max_val
    def validate(self, data: Any) -> ValidationResult:
        errors = []
        if self.min_val is not None and data < self.min_val:
            errors.append(f"Value {data} below minimum {self.min_val}")
        if self.max_val is not None and data > self.max_val:
            errors.append(f"Value {data} above maximum {self.max_val}")
        return ValidationResult(is_valid=len(errors)==0, errors=errors)

class ValidationEngine:
    def __init__(self) -> None:
        self._validators: dict[str, Validator] = {}
    def register(self, name: str, validator: Validator) -> None:
        self._validators[name] = validator
    def validate(self, name: str, data: Any) -> ValidationResult:
        if name not in self._validators:
            raise ValidationError(f"Validator '{name}' not found")
        return self._validators[name].validate(data)
    def validate_all(self, data: Any) -> dict[str, ValidationResult]:
        return {name: v.validate(data) for name, v in self._validators.items()}

