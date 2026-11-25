"""
Great Expectations Suite Builder Module.

Constructs Great Expectations ExpectationSuites dynamically from framework rule definitions or YAML configuration.
"""

from typing import List, Dict, Any, Optional
import logging
from src.dq_framework.quality_rule import QualityRule

logger = logging.getLogger(__name__)


class GESuiteBuilder:
    """
    Builder for generating Great Expectations suite configurations.
    """

    def __init__(self, suite_name: str = "default_dq_suite"):
        self.suite_name = suite_name
        self.expectations: List[Dict[str, Any]] = []

    def add_expectation(self, expectation_type: str, kwargs: Dict[str, Any], meta: Optional[Dict[str, Any]] = None):
        """Add an expectation definition to the suite."""
        self.expectations.append({
            "expectation_type": expectation_type,
            "kwargs": kwargs,
            "meta": meta or {},
        })

    def build_from_rules(self, rules: List[QualityRule]) -> Dict[str, Any]:
        """
        Map framework QualityRule objects into GE Expectation definitions.

        Args:
            rules: List of custom QualityRule instances.

        Returns:
            Dictionary representing Great Expectations Suite structure.
        """
        for r in rules:
            rule_cls_name = r.__class__.__name__

            if rule_cls_name == "NullCheckRule":
                cols = getattr(r, "columns", [])
                for col in cols:
                    self.add_expectation(
                        "expect_column_values_to_not_be_null",
                        {"column": col},
                        meta={"severity": r.severity.value, "dimension": r.dimension.value},
                    )

            elif rule_cls_name == "PrimaryKeyUniquenessRule":
                pk_cols = getattr(r, "pk_columns", [])
                if len(pk_cols) == 1:
                    self.add_expectation(
                        "expect_column_values_to_be_unique",
                        {"column": pk_cols[0]},
                        meta={"severity": r.severity.value, "dimension": r.dimension.value},
                    )
                elif len(pk_cols) > 1:
                    self.add_expectation(
                        "expect_compound_columns_to_be_unique",
                        {"column_list": pk_cols},
                        meta={"severity": r.severity.value, "dimension": r.dimension.value},
                    )

            elif rule_cls_name == "NumericRangeRule":
                col = getattr(r, "column", None)
                min_v = getattr(r, "min_val", None)
                max_v = getattr(r, "max_val", None)
                if col:
                    self.add_expectation(
                        "expect_column_values_to_be_between",
                        {"column": col, "min_value": min_v, "max_value": max_v},
                        meta={"severity": r.severity.value, "dimension": r.dimension.value},
                    )

            elif rule_cls_name == "ValueSetRule":
                col = getattr(r, "column", None)
                allowed = getattr(r, "allowed_values", [])
                if col:
                    self.add_expectation(
                        "expect_column_values_to_be_in_set",
                        {"column": col, "value_set": allowed},
                        meta={"severity": r.severity.value, "dimension": r.dimension.value},
                    )

            elif rule_cls_name == "RowCountRule":
                min_r = getattr(r, "min_rows", 1)
                max_r = getattr(r, "max_rows", None)
                self.add_expectation(
                    "expect_table_row_count_to_be_between",
                    {"min_value": min_r, "max_value": max_r},
                    meta={"severity": r.severity.value, "dimension": r.dimension.value},
                )

        return {
            "expectation_suite_name": self.suite_name,
            "expectations": self.expectations,
            "meta": {"created_by": "GESuiteBuilder"},
        }
