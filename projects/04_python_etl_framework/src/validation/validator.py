"""
Data Validation Module

Validates data quality and schema compliance for ETL pipelines.
"""

from typing import Any, Optional
from pydantic import BaseModel, ValidationError
import re


class ValidationRule(BaseModel):
    """Single validation rule."""
    column: str
    rule_type: str  # required, email, numeric, range, pattern
    params: dict[str, Any] = {}


class ValidationResult(BaseModel):
    """Result of validation check."""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class DataValidator:
    """
    Production data validator with configurable rules.
    """
    
    def __init__(self, rules: list[ValidationRule] | None = None):
        self.rules = rules or []
    
    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Validate all records against rules."""
        errors = []
        warnings = []
        
        for idx, record in enumerate(records):
            record_errors = self._validate_record(record, idx)
            errors.extend(record_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_record(self, record: dict[str, Any], row_idx: int) -> list[str]:
        """Validate single record against all rules."""
        errors = []
        
        for rule in self.rules:
            value = record.get(rule.column)
            
            if rule.rule_type == "required" and (value is None or value == ""):
                errors.append(f"Row {row_idx}: {rule.column} is required")
            
            elif rule.rule_type == "email" and value:
                if not self._validate_email(value):
                    errors.append(f"Row {row_idx}: {rule.column} is not a valid email")
            
            elif rule.rule_type == "numeric" and value is not None:
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(f"Row {row_idx}: {rule.column} must be numeric")
            
            elif rule.rule_type == "range" and value is not None:
                min_val = rule.params.get("min")
                max_val = rule.params.get("max")
                try:
                    num_val = float(value)
                    if min_val is not None and num_val < min_val:
                        errors.append(f"Row {row_idx}: {rule.column} below minimum")
                    if max_val is not None and num_val > max_val:
                        errors.append(f"Row {row_idx}: {rule.column} above maximum")
                except (ValueError, TypeError):
                    errors.append(f"Row {row_idx}: {rule.column} is not numeric")
            
            elif rule.rule_type == "pattern" and value:
                pattern = rule.params.get("regex", ".*")
                if not re.match(pattern, str(value)):
                    errors.append(f"Row {row_idx}: {rule.column} does not match pattern")
        
        return errors
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email))


class SchemaValidator:
    """
    Validates data schema and column presence.
    """
    
    def __init__(self, required_columns: list[str]):
        self.required_columns = set(required_columns)
    
    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Validate schema of records."""
        errors = []
        
        if not records:
            return ValidationResult(is_valid=False, errors=["No records to validate"])
        
        available_columns = set(records[0].keys())
        missing = self.required_columns - available_columns
        
        if missing:
            errors.append(f"Missing required columns: {', '.join(missing)}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)