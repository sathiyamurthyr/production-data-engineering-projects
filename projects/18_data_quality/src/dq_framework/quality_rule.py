import abc
import pandas as pd
from enum import Enum
from typing import List, Dict, Any, Optional

class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Dimension(str, Enum):
    COMPLETENESS = "COMPLETENESS"
    UNIQUENESS = "UNIQUENESS"
    VALIDITY = "VALIDITY"
    CONSISTENCY = "CONSISTENCY"
    TIMELINESS = "TIMELINESS"
    ACCURACY = "ACCURACY"

class RuleResult:
    """
    Represents the result of evaluating a single data quality rule.
    """
    def __init__(
        self,
        rule_name: str,
        dimension: Dimension,
        passed: bool,
        failed_count: int,
        passed_count: int,
        failed_indices: List[Any],
        details: Optional[Dict[str, Any]] = None,
        severity: Severity = Severity.ERROR,
        message: Optional[str] = None
    ):
        self.rule_name = rule_name
        self.dimension = dimension
        self.passed = passed
        self.failed_count = failed_count
        self.passed_count = passed_count
        self.failed_indices = failed_indices
        self.details = details or {}
        self.severity = severity
        
        self.total_count = failed_count + passed_count
        self.failed_percentage = (failed_count / self.total_count * 100.0) if self.total_count > 0 else 0.0
        
        if message is not None:
            self.message = message
        else:
            if passed:
                self.message = f"Passed validation for {self.rule_name}."
            else:
                self.message = f"Failed validation: found {failed_count} violations out of {self.total_count} records."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "dimension": self.dimension.value,
            "passed": self.passed,
            "failed_count": self.failed_count,
            "passed_count": self.passed_count,
            "total_count": self.total_count,
            "failed_percentage": self.failed_percentage,
            "failed_indices": self.failed_indices,
            "message": self.message,
            "details": self.details,
            "severity": self.severity.value
        }


class QualityRule(abc.ABC):
    """
    Abstract base class representing a single data quality rule.
    """
    def __init__(
        self,
        severity: Severity = Severity.ERROR,
        description: str = "",
        name: Optional[str] = None,
        **kwargs
    ):
        self.severity = severity
        self.description = description
        self.name = name or self.__class__.__name__
        self.kwargs = kwargs

    @property
    @abc.abstractmethod
    def dimension(self) -> Dimension:
        """Returns the data quality dimension this rule validates."""
        pass

    @abc.abstractmethod
    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        """
        Evaluates the rule against the input DataFrame.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.name,
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "description": self.description,
            **self.kwargs
        }
