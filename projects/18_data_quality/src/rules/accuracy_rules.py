import numpy as np
import pandas as pd
from typing import Optional
from src.dq_framework.quality_rule import QualityRule, RuleResult, Severity, Dimension
from src.dq_framework.rule_registry import RuleRegistry

@RuleRegistry.register("outlier_detection")
@RuleRegistry.register("accuracy_zscore")
class OutlierDetectionRule(QualityRule):
    """
    Validates numeric values by ensuring they are not extreme outliers using Z-score.
    """
    def __init__(
        self,
        column: str,
        threshold: float = 3.0,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.threshold = threshold

    @property
    def dimension(self) -> Dimension:
        return Dimension.ACCURACY

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
        clean_series = series.dropna()

        if len(clean_series) < 3:
            # Not enough data points to compute valid Z-score metrics
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=True,
                failed_count=0,
                passed_count=len(df),
                failed_indices=[],
                severity=self.severity
            )

        mean = clean_series.mean()
        std = clean_series.std()

        if std == 0:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=True,
                failed_count=0,
                passed_count=len(df),
                failed_indices=[],
                severity=self.severity
            )

        z_scores = (series - mean) / std
        failed_mask = series.notna() & (z_scores.abs() > self.threshold)

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
            details={"column": self.column, "mean": float(mean), "std": float(std), "threshold": self.threshold},
            severity=self.severity
        )


@RuleRegistry.register("statistical_range")
class StatisticalRangeRule(QualityRule):
    """
    Validates numeric values by ensuring they fall within IQR bounds (Q1 - factor*IQR to Q3 + factor*IQR).
    """
    def __init__(
        self,
        column: str,
        factor: float = 1.5,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.column = column
        self.factor = factor

    @property
    def dimension(self) -> Dimension:
        return Dimension.ACCURACY

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
        clean_series = series.dropna()

        if len(clean_series) < 4:
            return RuleResult(
                rule_name=self.name,
                dimension=self.dimension,
                passed=True,
                failed_count=0,
                passed_count=len(df),
                failed_indices=[],
                severity=self.severity
            )

        q25 = clean_series.quantile(0.25)
        q75 = clean_series.quantile(0.75)
        iqr = q75 - q25
        lower_bound = q25 - self.factor * iqr
        upper_bound = q75 + self.factor * iqr

        failed_mask = series.notna() & ((series < lower_bound) | (series > upper_bound))
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
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "iqr": float(iqr)
            },
            severity=self.severity
        )


@RuleRegistry.register("accuracy_formula")
class FormulaAccuracyRule(QualityRule):
    """
    Validates mathematical relations or formulas between columns in the same row.
    """
    def __init__(
        self,
        formula: str,
        severity: Severity = Severity.ERROR,
        description: str = "",
        **kwargs
    ):
        super().__init__(severity=severity, description=description, **kwargs)
        self.formula = formula

    @property
    def dimension(self) -> Dimension:
        return Dimension.ACCURACY

    def evaluate(self, df: pd.DataFrame) -> RuleResult:
        try:
            result = df.eval(self.formula)
            if isinstance(result, pd.Series):
                valid_mask = result.astype(bool)
            else:
                valid_mask = pd.Series(result, index=df.index)
        except Exception as e:
            valid_mask = pd.Series(False, index=df.index)

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
            details={"formula": self.formula},
            severity=self.severity
        )
