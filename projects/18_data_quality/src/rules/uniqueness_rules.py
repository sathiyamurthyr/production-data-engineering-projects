import pandas as pd
from typing import Optional, Any, List
from src.dq_framework.quality_rule import QualityRule, RuleResult, Severity, Dimension
from src.dq_framework.rule_registry import RuleRegistry

@RuleRegistry.register("uniqueness")
class PrimaryKeyUniquenessRule(QualityRule):
    """
    Validates that a designated primary key column contains unique values.
    """
    def __init__(
        self,
        pk_column: Optional[str] = None,
        column: Optional[str] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.pk_column = pk_column or column
        if not self.pk_column:
            raise ValueError("PrimaryKeyUniquenessRule requires either 'pk_column' or 'column' to be specified.")
        self.pk_columns = [self.pk_column]

    @property
    def dimension(self) -> Dimension:
        return Dimension.UNIQUENESS

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.pk_column not in df.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": f"Column '{self.pk_column}' not found"},
                severity=self.severity
            )

        col = df[self.pk_column]
        # Keep=False to flag all duplicate occurrences (both/all duplicates)
        duplicated_mask = col.duplicated(keep=False)

        failed_indices = df.index[duplicated_mask].tolist()
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
            details={"pk_column": self.pk_column},
            severity=self.severity
        )


@RuleRegistry.register("duplicate_rows")
class DuplicateRowsRule(QualityRule):
    """
    Validates that there are no completely identical duplicate rows across the entire dataset.
    """
    def __init__(
        self,
        severity: Severity = Severity.WARNING,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)

    @property
    def dimension(self) -> Dimension:
        return Dimension.UNIQUENESS

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        duplicated_mask = df.duplicated(keep=False)
        failed_indices = df.index[duplicated_mask].tolist()
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
            details={},
            severity=self.severity
        )
