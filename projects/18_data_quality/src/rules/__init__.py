"""
Data Quality Rules Package.
"""

from src.rules.completeness_rules import NullCheckRule, RowCountRule, RequiredColumnsRule
from src.rules.uniqueness_rules import PrimaryKeyUniquenessRule, DuplicateRowsRule
from src.rules.validity_rules import EmailFormatRule, NumericRangeRule, ValueSetRule, RegexMatchRule, DateRangeRule
from src.rules.consistency_rules import ReferentialIntegrityRule, CrossColumnComparisonRule
from src.rules.timeliness_rules import TimelinessRule, FreshnessRule, DataSlaRule
from src.rules.accuracy_rules import OutlierDetectionRule, StatisticalRangeRule

__all__ = [
    "NullCheckRule",
    "RowCountRule",
    "RequiredColumnsRule",
    "PrimaryKeyUniquenessRule",
    "DuplicateRowsRule",
    "EmailFormatRule",
    "NumericRangeRule",
    "ValueSetRule",
    "RegexMatchRule",
    "DateRangeRule",
    "ReferentialIntegrityRule",
    "CrossColumnComparisonRule",
    "TimelinessRule",
    "FreshnessRule",
    "DataSlaRule",
    "OutlierDetectionRule",
    "StatisticalRangeRule",
]
