import re
import pandas as pd
from typing import List, Any, Optional
from src.dq_framework.quality_rule import QualityRule, RuleResult, Severity, Dimension
from src.dq_framework.rule_registry import RuleRegistry

@RuleRegistry.register("validity_email")
class EmailFormatRule(QualityRule):
    """
    Validates that values in the target column conform to standard email format.
    """
    def __init__(
        self,
        column: str,
        severity: Severity = Severity.WARNING,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        # Default RFC 5322 regex pattern
        pattern_str = kwargs.get("regex", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        self.pattern = re.compile(pattern_str)

    @property
    def dimension(self) -> Dimension:
        return Dimension.VALIDITY

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.column not in df.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": f"Column '{self.column}' not found"},
                severity=self.severity
            )

        series = df[self.column]

        def check_email(val):
            # Nulls are passed so completeness checks catch them instead of duplicate warnings
            if pd.isna(val) or val is None:
                return True
            return bool(self.pattern.match(str(val)))

        valid_mask = series.apply(check_email)
        failed_mask = ~valid_mask
        failed_indices = df.index[failed_mask].tolist()
        failed_count = len(failed_indices)
        passed_count = len(df) - failed_count
        passed = failed_count == 0

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details={"column": self.column},
            severity=self.severity
        )


@RuleRegistry.register("validity_range")
class NumericRangeRule(QualityRule):
    """
    Validates that a numeric column falls within a specified range [min_val, max_val].
    """
    def __init__(
        self,
        column: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.min_val = min_val if min_val is not None else min_value
        self.max_val = max_val if max_val is not None else max_value

    @property
    def dimension(self) -> Dimension:
        return Dimension.VALIDITY

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.column not in df.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": f"Column '{self.column}' not found"},
                severity=self.severity
            )

        series = pd.to_numeric(df[self.column], errors='coerce')
        # Original non-null values that failed numeric coercion are invalid
        coercion_failed = df[self.column].notna() & series.isna()

        valid_mask = pd.Series(True, index=df.index)
        valid_mask[coercion_failed] = False

        if self.min_val is not None:
            valid_mask = valid_mask & (series.isna() | (series >= self.min_val))
        if self.max_val is not None:
            valid_mask = valid_mask & (series.isna() | (series <= self.max_val))

        failed_mask = ~valid_mask
        failed_indices = df.index[failed_mask].tolist()
        failed_count = len(failed_indices)
        passed_count = len(df) - failed_count
        passed = failed_count == 0

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details={"column": self.column, "min_val": self.min_val, "max_val": self.max_val},
            severity=self.severity
        )


@RuleRegistry.register("value_set")
@RuleRegistry.register("validity_country")
class ValueSetRule(QualityRule):
    """
    Validates that a column's values belong to a defined set of allowed values.
    """
    def __init__(
        self,
        column: str,
        allowed_values: List[Any],
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.allowed_values = allowed_values
        self.ignore_case = kwargs.get("ignore_case", False)

    @property
    def dimension(self) -> Dimension:
        return Dimension.VALIDITY

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.column not in df.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": f"Column '{self.column}' not found"},
                severity=self.severity
            )

        series = df[self.column]

        if self.ignore_case:
            allowed_set = {str(v).strip().lower() for v in self.allowed_values}
            def check_val(val):
                if pd.isna(val) or val is None:
                    return True
                return str(val).strip().lower() in allowed_set
        else:
            allowed_set = set(self.allowed_values)
            def check_val(val):
                if pd.isna(val) or val is None:
                    return True
                return val in allowed_set

        valid_mask = series.apply(check_val)
        failed_mask = ~valid_mask
        failed_indices = df.index[failed_mask].tolist()
        failed_count = len(failed_indices)
        passed_count = len(df) - failed_count
        passed = failed_count == 0

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details={"column": self.column, "allowed_values": self.allowed_values},
            severity=self.severity
        )


@RuleRegistry.register("regex_match")
@RuleRegistry.register("validity_phone")
class RegexMatchRule(QualityRule):
    """
    Validates that text values in a column match a specific regular expression.
    """
    def __init__(
        self,
        column: str,
        pattern: Optional[str] = None,
        regex: Optional[str] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        pattern_str = pattern or regex
        if not pattern_str:
            # Default international phone pattern if not provided
            pattern_str = r"^\+?[1-9]\d{1,14}([-.\s]?\d+)*$"
        self.pattern_str = pattern_str
        self.pattern = re.compile(pattern_str)

    @property
    def dimension(self) -> Dimension:
        return Dimension.VALIDITY

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.column not in df.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": f"Column '{self.column}' not found"},
                severity=self.severity
            )

        series = df[self.column]

        def check_regex(val):
            if pd.isna(val) or val is None:
                return True
            return bool(self.pattern.match(str(val)))

        valid_mask = series.apply(check_regex)
        failed_mask = ~valid_mask
        failed_indices = df.index[failed_mask].tolist()
        failed_count = len(failed_indices)
        passed_count = len(df) - failed_count
        passed = failed_count == 0

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details={"column": self.column, "pattern": self.pattern_str},
            severity=self.severity
        )


@RuleRegistry.register("date_range")
class DateRangeRule(QualityRule):
    """
    Validates that dates in a column fall within a specified date window.
    """
    def __init__(
        self,
        column: str,
        min_date: Optional[str] = None,
        max_date: Optional[str] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.min_date = pd.to_datetime(min_date) if min_date else None
        self.max_date = pd.to_datetime(max_date) if max_date else None

    @property
    def dimension(self) -> Dimension:
        return Dimension.VALIDITY

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.column not in df.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": f"Column '{self.column}' not found"},
                severity=self.severity
            )

        series = pd.to_datetime(df[self.column], errors='coerce')
        coercion_failed = df[self.column].notna() & series.isna()

        valid_mask = pd.Series(True, index=df.index)
        valid_mask[coercion_failed] = False

        if self.min_date is not None:
            valid_mask = valid_mask & (series.isna() | (series >= self.min_date))
        if self.max_date is not None:
            valid_mask = valid_mask & (series.isna() | (series <= self.max_date))

        failed_mask = ~valid_mask
        failed_indices = df.index[failed_mask].tolist()
        failed_count = len(failed_indices)
        passed_count = len(df) - failed_count
        passed = failed_count == 0

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details={"column": self.column, "min_date": str(self.min_date), "max_date": str(self.max_date)},
            severity=self.severity
        )
