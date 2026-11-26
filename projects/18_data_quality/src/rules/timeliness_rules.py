import pandas as pd
from typing import Optional
from src.dq_framework.quality_rule import QualityRule, RuleResult, Severity, Dimension
from src.dq_framework.rule_registry import RuleRegistry

@RuleRegistry.register("timeliness_future")
class FutureDateTimelinessRule(QualityRule):
    """
    Validates that a date/timestamp field does not contain future dates relative to execution time.
    """
    def __init__(
        self,
        column: str,
        reference_date: Optional[str] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.reference_date = reference_date

    @property
    def dimension(self) -> Dimension:
        return Dimension.TIMELINESS

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

        col_dt = pd.to_datetime(df[self.column], errors='coerce')
        conversion_failed = df[self.column].notna() & col_dt.isna()

        ref_date = pd.to_datetime(self.reference_date) if self.reference_date else pd.Timestamp.now()

        valid_mask = pd.Series(True, index=df.index)
        valid_mask[conversion_failed] = False
        valid_mask = valid_mask & (col_dt.isna() | (col_dt <= ref_date))

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
            details={"column": self.column, "reference_date": str(ref_date)},
            severity=self.severity
        )


@RuleRegistry.register("timeliness")
class TimelinessRule(QualityRule):
    """
    Validates that events in a column are processed/arrived within a threshold delay.
    """
    def __init__(
        self,
        column: str,
        max_delay_hours: float = 24.0,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.max_delay_hours = max_delay_hours

    @property
    def dimension(self) -> Dimension:
        return Dimension.TIMELINESS

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

        col_dt = pd.to_datetime(df[self.column], errors='coerce')
        conversion_failed = df[self.column].notna() & col_dt.isna()

        now = pd.Timestamp.now()
        valid_mask = pd.Series(True, index=df.index)
        valid_mask[conversion_failed] = False

        delays = (now - col_dt).dt.total_seconds() / 3600.0
        valid_mask = valid_mask & (col_dt.isna() | (delays <= self.max_delay_hours))

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
            details={"column": self.column, "max_delay_hours": self.max_delay_hours},
            severity=self.severity
        )


@RuleRegistry.register("freshness")
class FreshnessRule(QualityRule):
    """
    Validates dataset freshness by checking if the latest timestamp in the column is within the SLA.
    This is a table-level validation rule.
    """
    def __init__(
        self,
        column: str,
        max_age_hours: float = 24.0,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.max_age_hours = max_age_hours

    @property
    def dimension(self) -> Dimension:
        return Dimension.TIMELINESS

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.column not in df.columns or len(df) == 0:
            passed = len(df) == 0  # Pass if empty dataset is expected, otherwise fail.
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=passed,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": "Empty dataset or column not found"},
                severity=self.severity
            )

        col_dt = pd.to_datetime(df[self.column], errors='coerce').dropna()
        if len(col_dt) == 0:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": "All date values are null/coercion failed"},
                severity=self.severity
            )

        latest_timestamp = col_dt.max()
        now = pd.Timestamp.now()
        age_hours = (now - latest_timestamp).total_seconds() / 3600.0
        passed = age_hours <= self.max_age_hours

        failed_count = 0 if passed else len(df)
        passed_count = len(df) if passed else 0
        failed_indices = [] if passed else df.index.tolist()

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details={
                "column": self.column,
                "latest_timestamp": str(latest_timestamp),
                "age_hours": round(age_hours, 2),
                "max_age_hours": self.max_age_hours
            },
            severity=self.severity
        )


@RuleRegistry.register("data_sla")
class DataSlaRule(QualityRule):
    """
    Checks if a dataset has arrived/contains data before a specific target hour of the day.
    """
    def __init__(
        self,
        target_hour: int = 8,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.target_hour = target_hour

    @property
    def dimension(self) -> Dimension:
        return Dimension.TIMELINESS

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        now = pd.Timestamp.now()
        passed = True
        if now.hour >= self.target_hour and len(df) == 0:
            passed = False

        failed_count = 0 if passed else len(df)
        passed_count = len(df) if passed else 0
        failed_indices = [] if passed else df.index.tolist()

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details={"current_time": str(now), "target_hour": self.target_hour},
            severity=self.severity
        )
