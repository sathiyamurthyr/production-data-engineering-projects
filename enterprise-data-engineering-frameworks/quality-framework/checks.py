"""Data quality: schema, business rules, duplicates, freshness, completeness."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import utc_now_iso

@dataclass
class QualityResult:
    check_name: str; passed: bool; score: float=0.0
    details: dict[str,Any]=field(default_factory=dict)
    errors: list[str]=field(default_factory=list); timestamp: str=field(default_factory=utc_now_iso)

class QualityCheck(ABC):
    def __init__(self, name): self.name=name
    @abstractmethod
    def check(self, data) -> QualityResult: ...

class SchemaCheck(QualityCheck):
    def __init__(self, schema, name="schema"): super().__init__(name); self.schema=schema
    def check(self, data):
        e=[]
        for i,r in enumerate(data):
            for f,t in self.schema.items():
                if f not in r: e.append(f"Record {i}: missing '{f}'")
                elif not isinstance(r[f], t): e.append(f"Record {i}: '{f}' wrong type")
        s=1.0-len(e)/max(len(data)*len(self.schema),1)
        return QualityResult(self.name, len(e)==0, s, errors=e)

class CompletenessCheck(QualityCheck):
    def __init__(self, fields, name="completeness"): super().__init__(name); self.fields=fields
    def check(self, data):
        total=len(data)*len(self.fields); miss=sum(1 for r in data for f in self.fields if r.get(f) is None)
        return QualityResult(self.name, miss==0, 1-miss/max(total,1), {"missing":miss})

class DuplicateCheck(QualityCheck):
    def __init__(self, keys, name="duplicates"): super().__init__(name); self.keys=keys
    def check(self, data):
        seen=set(); dups=0
        for r in data:
            k=tuple(r.get(f) for f in self.keys)
            if k in seen: dups+=1
            else: seen.add(k)
        return QualityResult(self.name, dups==0, 1-dups/max(len(data),1), {"duplicates":dups})

class BusinessRuleCheck(QualityCheck):
    def __init__(self, rule, name="business_rule"): super().__init__(name); self.rule=rule
    def check(self, data):
        v=[i for i,r in enumerate(data) if not self.rule(r)]
        return QualityResult(self.name, len(v)==0, 1-len(v)/max(len(data),1), {"violations":len(v)})

class QualityReporter:
    def __init__(self): self._r=[]
    def run_checks(self, data, checks):
        r=[c.check(data) for c in checks]; self._r.extend(r); return r
    def overall_score(self): return sum(r.score for r in self._r)/max(len(self._r),1)
    def all_passed(self): return all(r.passed for r in self._r)

