"""Data validation with contracts and custom validators."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from shared.exceptions import ValidationError

@dataclass
class ValidationRule:
    name: str; field_name: str; rule_type: str; params: dict[str,Any]=field(default_factory=dict)

@dataclass
class ValidationReport:
    is_valid: bool; errors: list[str]=field(default_factory=list)
    rules_checked: int=0; rules_passed: int=0

class DataContract:
    def __init__(self, name): self.name=name; self.rules=[]
    def add_rule(self, r): self.rules.append(r); return self
    def validate(self, data):
        e=[]; p=0
        for r in self.rules:
            v=data.get(r.field_name)
            if r.rule_type=="required" and v is None: e.append(f"{r.field_name} is required")
            elif r.rule_type=="type" and v is not None and not isinstance(v, r.params.get("type")): e.append(f"{r.field_name} wrong type")
            elif r.rule_type=="min" and v is not None and v<r.params.get("min",0): e.append(f"{r.field_name} below min")
            elif r.rule_type=="max" and v is not None and v>r.params.get("max",0): e.append(f"{r.field_name} above max")
            elif r.rule_type=="regex" and v is not None:
                import re
                if not re.match(r.params.get("pattern",""), str(v)): e.append(f"{r.field_name} no match")
            else: p+=1
        return ValidationReport(len(e)==0, e, len(self.rules), p)

class ValidationEngine:
    def __init__(self): self._contracts={}
    def register_contract(self, c): self._contracts[c.name]=c
    def validate(self, name, data):
        if name not in self._contracts: raise ValidationError(f"Contract '{name}' not found")
        return self._contracts[name].validate(data)

