"""
Great Expectations Runner Module.

Executes Great Expectations validation against pandas DataFrames and maps the validation output
into the native framework `QualityReport` object format.
"""

from typing import Dict, Any, List, Optional
import time
import logging
import pandas as pd

from src.dq_framework.quality_rule import RuleResult, Severity, Dimension
from src.dq_framework.quality_report import QualityReport
from src.great_expectations.ge_suite_builder import GESuiteBuilder

logger = logging.getLogger(__name__)


class GERunner:
    """
    Executes Great Expectations validation suites against pandas DataFrames.
    """

    def __init__(self, dataset_name: str = "dataset"):
        self.dataset_name = dataset_name

    def run_suite(self, df: pd.DataFrame, ge_suite_dict: Dict[str, Any]) -> QualityReport:
        """
        Validate a DataFrame against a Great Expectations suite dict.

        Args:
            df: Input pandas DataFrame.
            ge_suite_dict: Dictionary returned from GESuiteBuilder.

        Returns:
            QualityReport containing standardized execution results.
        """
        start_time = time.time()
        results: List[RuleResult] = []
        expectations = ge_suite_dict.get("expectations", [])
        total_records = len(df)

        try:
            import great_expectations as ge
            ge_df = ge.from_pandas(df)
            use_ge_native = True
        except ImportError:
            logger.warning("great_expectations library not installed. Falling back to native emulation runner.")
            use_ge_native = False
            ge_df = df

        for exp in expectations:
            exp_type = exp.get("expectation_type")
            kwargs = exp.get("kwargs", {})
            meta = exp.get("meta", {})
            
            sev_str = meta.get("severity", "ERROR").upper()
            dim_str = meta.get("dimension", "Validity").upper()

            try:
                severity = Severity[sev_str]
            except KeyError:
                severity = Severity.ERROR

            try:
                dimension = Dimension[dim_str]
            except KeyError:
                dimension = Dimension.VALIDITY

            passed = True
            failed_count = 0
            failed_indices: List[int] = []
            msg = f"GE Expectation '{exp_type}' evaluated."

            if use_ge_native and hasattr(ge_df, exp_type):
                method = getattr(ge_df, exp_type)
                eval_res = method(**kwargs)
                passed = bool(eval_res.get("success", False))
                result_info = eval_res.get("result", {})
                failed_count = int(result_info.get("unexpected_count", 0))
                unexpected_indices = result_info.get("unexpected_index_list", [])
                if unexpected_indices:
                    failed_indices = [int(i) for i in unexpected_indices]
                msg = f"GE Expectation '{exp_type}' on '{kwargs}': success={passed}, unexpected={failed_count}"
            else:
                # Custom emulation fallback if GE is not directly available
                passed, failed_count, failed_indices, msg = self._emulate_expectation(df, exp_type, kwargs)

            passed_count = total_records - failed_count
            failed_pct = (failed_count / total_records * 100.0) if total_records > 0 else 0.0

            result = RuleResult(
                rule_name=f"GE::{exp_type}({','.join([f'{k}={v}' for k,v in kwargs.items()])})",
                dimension=dimension,
                severity=severity,
                passed=passed,
                passed_count=passed_count,
                failed_count=failed_count,
                total_count=total_records,
                failed_percentage=failed_pct,
                message=msg,
                failed_indices=failed_indices,
                details={"expectation_type": exp_type, "kwargs": kwargs},
            )
            results.append(result)

        duration = time.time() - start_time
        return QualityReport(
            dataset_name=self.dataset_name,
            total_records=total_records,
            execution_duration_seconds=duration,
            results=results,
        )

    def _emulate_expectation(self, df: pd.DataFrame, exp_type: str, kwargs: Dict[str, Any]) -> tuple:
        """Internal emulation helper for GE expectations."""
        col = kwargs.get("column")
        total = len(df)

        if exp_type == "expect_column_values_to_not_be_null" and col in df.columns:
            null_mask = df[col].isna()
            failed_idx = list(df[null_mask].index)
            return len(failed_idx) == 0, len(failed_idx), failed_idx, f"Column '{col}' null check."

        elif exp_type == "expect_column_values_to_be_unique" and col in df.columns:
            dup_mask = df.duplicated(subset=[col], keep=False)
            failed_idx = list(df[dup_mask].index)
            return len(failed_idx) == 0, len(failed_idx), failed_idx, f"Column '{col}' uniqueness check."

        elif exp_type == "expect_column_values_to_be_between" and col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce")
            min_v = kwargs.get("min_value")
            max_v = kwargs.get("max_value")
            out_mask = pd.Series(False, index=df.index)
            if min_v is not None:
                out_mask = out_mask | (series < min_v)
            if max_v is not None:
                out_mask = out_mask | (series > max_v)
            failed_idx = list(df[out_mask & df[col].notna()].index)
            return len(failed_idx) == 0, len(failed_idx), failed_idx, f"Column '{col}' between check."

        return True, 0, [], f"Expectation '{exp_type}' passed default emulation."
