import pandas as pd
from typing import List, Optional, Any
from src.dq_framework.quality_rule import QualityRule, RuleResult, Severity, Dimension
from src.dq_framework.rule_registry import RuleRegistry

@RuleRegistry.register("completeness")
class NullCheckRule(QualityRule):
    """
    Validates that specified columns do not contain null, NaN, or empty values.
    Can be configured with a list of columns or a single column.
    """
    def __init__(
        self,
        columns: Optional[List[str]] = None,
        column: Optional[str] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        if columns is None and column is not None:
            self.columns = [column]
        elif columns is not None:
            self.columns = columns
        else:
            self.columns = []

    @property
    def dimension(self) -> Dimension:
        return Dimension.COMPLETENESS

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if not self.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=True,
                failed_count=0,
                passed_count=len(df),
                failed_indices=[],
                severity=self.severity
            )

        failed_mask = pd.Series(False, index=df.index)
        for col in self.columns:
            if col not in df.columns:
                failed_mask = failed_mask | pd.Series(True, index=df.index)
            else:
                series = df[col]
                # NA / Null values
                is_null = series.isna()
                # Empty / whitespace-only string values
                is_empty_str = series.apply(lambda x: isinstance(x, str) and not x.strip())
                failed_mask = failed_mask | is_null | is_empty_str

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
            details={"columns": self.columns},
            severity=self.severity
        )


@RuleRegistry.register("row_count")
class RowCountRule(QualityRule):
    """
    Validates that the total number of records in the DataFrame falls within the specified limits.
    """
    def __init__(
        self,
        min_rows: Optional[int] = None,
        max_rows: Optional[int] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.min_rows = min_rows
        self.max_rows = max_rows

    @property
    def dimension(self) -> Dimension:
        return Dimension.COMPLETENESS

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        row_count = len(df)
        passed = True
        details = {"row_count": row_count, "min_rows": self.min_rows, "max_rows": self.max_rows}

        if self.min_rows is not None and row_count < self.min_rows:
            passed = False
        if self.max_rows is not None and row_count > self.max_rows:
            passed = False

        failed_count = 0 if passed else row_count
        passed_count = row_count if passed else 0
        failed_indices = [] if passed else df.index.tolist()

        return RuleResult(
            rule_name=self.name,
            dimension=self.dimension,
            passed=passed,
            failed_count=failed_count,
            passed_count=passed_count,
            failed_indices=failed_indices,
            details=details,
            severity=self.severity
        )


@RuleRegistry.register("required_columns")
class RequiredColumnsRule(QualityRule):
    """
    Validates that all expected columns are present in the DataFrame schema.
    """
    def __init__(
        self,
        expected_columns: List[str],
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.expected_columns = expected_columns

    @property
    def dimension(self) -> Dimension:
        return Dimension.COMPLETENESS

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        missing_columns = [col for col in self.expected_columns if col not in df.columns]
        passed = len(missing_columns) == 0
        details = {"expected_columns": self.expected_columns, "missing_columns": missing_columns}

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
            details=details,
            severity=self.severity
        )
