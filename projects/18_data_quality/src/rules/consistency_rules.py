import pandas as pd
from typing import Optional, List, Any, Set
from src.dq_framework.quality_rule import QualityRule, RuleResult, Severity, Dimension
from src.dq_framework.rule_registry import RuleRegistry

@RuleRegistry.register("consistency_ref_integrity")
class ReferentialIntegrityRule(QualityRule):
    """
    Validates referential integrity by checking if foreign key values exist in parent table's keys.
    """
    def __init__(
        self,
        column: str,
        parent_table: Optional[str] = None,
        parent_key: Optional[str] = "customer_id",
        parent_ids: Optional[Any] = None,
        parent_df: Optional[pd.DataFrame] = None,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.parent_table = parent_table
        self.parent_key = parent_key
        self.parent_ids = parent_ids
        self.parent_df = parent_df

    @property
    def dimension(self) -> Dimension:
        return Dimension.CONSISTENCY

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

        # Resolve parent keys into a set for fast lookup
        resolved_ids: Set[Any] = set()
        if self.parent_ids is not None:
            if isinstance(self.parent_ids, (set, list, tuple)):
                resolved_ids = set(self.parent_ids)
            else:
                resolved_ids = {self.parent_ids}
        elif self.parent_df is not None and self.parent_key in self.parent_df.columns:
            resolved_ids = set(self.parent_df[self.parent_key].dropna().unique())

        col = df[self.column]

        def check_ref(val):
            # Nulls are allowed in optional relationships
            if pd.isna(val) or val is None:
                return True
            return val in resolved_ids

        valid_mask = col.apply(check_ref)
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
            details={
                "column": self.column,
                "parent_table": self.parent_table,
                "parent_key": self.parent_key,
                "resolved_keys_count": len(resolved_ids)
            },
            severity=self.severity
        )


@RuleRegistry.register("cross_column_comparison")
class CrossColumnComparisonRule(QualityRule):
    """
    Validates logical relations between two columns in the same row (e.g. col_a > col_b).
    """
    def __init__(
        self,
        column: str,
        comparison_column: str,
        operator: str = "==",
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.comparison_column = comparison_column
        self.operator = operator

    @property
    def dimension(self) -> Dimension:
        return Dimension.CONSISTENCY

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        if self.column not in df.columns or self.comparison_column not in df.columns:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=False,
                failed_count=len(df),
                passed_count=0,
                failed_indices=df.index.tolist(),
                details={"error": "One or both comparison columns not found"},
                severity=self.severity
            )

        col_a = df[self.column]
        col_b = df[self.comparison_column]

        if self.operator == "==":
            valid_mask = col_a == col_b
        elif self.operator == "!=":
            valid_mask = col_a != col_b
        elif self.operator == ">":
            valid_mask = col_a > col_b
        elif self.operator == ">=":
            valid_mask = col_a >= col_b
        elif self.operator == "<":
            valid_mask = col_a < col_b
        elif self.operator == "<=":
            valid_mask = col_a <= col_b
        else:
            valid_mask = pd.Series(False, index=df.index)

        # Ignore null entries (passed by default, completeness checks catch them)
        valid_mask = valid_mask | col_a.isna() | col_b.isna()

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
            details={
                "column": self.column,
                "comparison_column": self.comparison_column,
                "operator": self.operator
            },
            severity=self.severity
        )
