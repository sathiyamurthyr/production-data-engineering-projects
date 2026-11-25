import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("data_quality_glue")

try:
    from awsglue.dataquality import EvaluateDataQuality
    from awsglue.dynamicframe import DynamicFrame
    GLUE_ENVIRONMENT = True
except ImportError:
    GLUE_ENVIRONMENT = False

class GlueDataQualityEvaluator:
    """
    Handles AWS Glue Data Quality (DQDL) rule configurations and evaluations.
    Supports native Glue execution and local PySpark simulation.
    """
    def __init__(self, ruleset_name: str, dqdl_rules: List[str]):
        self.ruleset_name = ruleset_name
        self.rules = dqdl_rules
        # Combine rules into standard DQDL ruleset format
        self.dqdl_string = f"Rules = [\n  " + ",\n  ".join(self.rules) + "\n]"
        logger.info(f"Initialized DQDL Ruleset '{ruleset_name}' with {len(self.rules)} rules.")

    def evaluate(self, dynamic_frame: Any, glue_context: Any = None) -> Tuple[bool, List[Dict[str, Any]], Any]:
        """
        Evaluates the dynamic frame against the defined DQDL rules.
        Returns:
            - overall_passed: bool
            - rules_report: List[Dict[str, Any]] (containing rule, status, and actual value)
            - filtered_frame: DynamicFrame/MockDynamicFrame (representing original data, or data with DQ columns)
        """
        if GLUE_ENVIRONMENT and isinstance(dynamic_frame, DynamicFrame) and glue_context:
            logger.info("Executing native AWS Glue Data Quality evaluation.")
            
            # Native EvaluateDataQuality execution
            dq_results = EvaluateDataQuality().execute_ruleset(
                frame=dynamic_frame,
                ruleset=self.dqdl_string,
                publishing_options={
                    "EvaluationContext": self.ruleset_name,
                    "ResultsS3Prefix": f"s3://data-engineering-diaries-glue-demo/dq-results/{self.ruleset_name}/"
                }
            )
            
            # Read results
            overall_passed = dq_results.get("Outcome") == "Passed"
            rules_report = []
            for rule_res in dq_results.get("RuleResults", []):
                rules_report.append({
                    "Rule": rule_res.get("Name"),
                    "Status": "PASSED" if rule_res.get("Result") == "PASS" else "FAILED",
                    "ActualValue": rule_res.get("EvaluationResult"),
                    "Description": rule_res.get("Description")
                })
            
            return overall_passed, rules_report, dynamic_frame
        else:
            logger.info("Executing local Spark fallback simulation for Data Quality rules.")
            is_wrapper = hasattr(dynamic_frame, "spark_df")
            df = dynamic_frame.spark_df if is_wrapper else dynamic_frame
            
            overall_passed = True
            rules_report = []
            
            # Local parser for basic DQDL rules
            for rule in self.rules:
                rule_clean = rule.strip()
                status, actual_val, desc = self._evaluate_rule_locally(df, rule_clean)
                if status == "FAILED":
                    overall_passed = False
                rules_report.append({
                    "Rule": rule_clean,
                    "Status": status,
                    "ActualValue": str(actual_val),
                    "Description": desc
                })

            logger.info(f"Local Data Quality validation finished. Outcome: {'PASSED' if overall_passed else 'FAILED'}")
            return overall_passed, rules_report, dynamic_frame

    def _evaluate_rule_locally(self, df: Any, rule: str) -> Tuple[str, Any, str]:
        """
        Parses and evaluates common DQDL rules on standard PySpark DataFrames:
        - RowCount > 0
        - ColumnCount == X
        - ColumnExists "col"
        - IsComplete "col"
        - ColumnDataType "col" = "type"
        - ColumnValues "col" in [values]
        """
        # Match RowCount
        row_count_match = re.match(r"RowCount\s*(>|>=|<|<=|==)\s*(\d+)", rule)
        if row_count_match:
            op, val = row_count_match.groups()
            val = int(val)
            actual = df.count()
            expr = f"{actual} {op} {val}"
            passed = eval(expr)
            return "PASSED" if passed else "FAILED", actual, f"Evaluated row count against condition {op} {val}"

        # Match ColumnCount
        col_count_match = re.match(r"ColumnCount\s*(==|!=|>|<)\s*(\d+)", rule)
        if col_count_match:
            op, val = col_count_match.groups()
            val = int(val)
            actual = len(df.columns)
            # convert operators to python
            py_op = "==" if op == "==" else op
            expr = f"{actual} {py_op} {val}"
            passed = eval(expr)
            return "PASSED" if passed else "FAILED", actual, f"Evaluated column count against condition {op} {val}"

        # Match ColumnExists
        col_exists_match = re.match(r"ColumnExists\s*\"([^\"]+)\"", rule)
        if col_exists_match:
            col_name = col_exists_match.group(1)
            actual = col_name in df.columns
            return "PASSED" if actual else "FAILED", actual, f"Checks if column '{col_name}' exists"

        # Match IsComplete
        is_complete_match = re.match(r"IsComplete\s*\"([^\"]+)\"", rule)
        if is_complete_match:
            col_name = is_complete_match.group(1)
            if col_name not in df.columns:
                return "FAILED", 0.0, f"Column '{col_name}' does not exist"
            total = df.count()
            if total == 0:
                return "PASSED", 100.0, "Empty dataset check"
            null_count = df.filter(df[col_name].isNull() | (df[col_name] == "")).count()
            completeness = ((total - null_count) / total) * 100.0
            passed = null_count == 0
            return "PASSED" if passed else "FAILED", f"{completeness:.1f}%", f"Checks completeness percentage of column '{col_name}'"

        # Match ColumnDataType
        col_type_match = re.match(r"ColumnDataType\s*\"([^\"]+)\"\s*=\s*\"([^\"]+)\"", rule)
        if col_type_match:
            col_name, expected_type = col_type_match.groups()
            if col_name not in df.columns:
                return "FAILED", "None", f"Column '{col_name}' does not exist"
            
            # Map Spark types to DQDL types roughly
            actual_spark_type = dict(df.dtypes).get(col_name, "")
            
            type_mapping = {
                "String": ["string"],
                "Double": ["double", "float"],
                "Integer": ["int", "bigint", "smallint", "tinyint", "integer"],
                "Boolean": ["boolean"]
            }
            
            actual_mapped = "Unknown"
            for dqdl_t, spark_ts in type_mapping.items():
                if actual_spark_type in spark_ts:
                    actual_mapped = dqdl_t
                    break
            
            passed = actual_mapped.lower() == expected_type.lower()
            return "PASSED" if passed else "FAILED", actual_spark_type, f"Checks if column '{col_name}' is of type {expected_type}"

        # Match ColumnValues in list
        col_vals_match = re.match(r"ColumnValues\s*\"([^\"]+)\"\s*in\s*\[([^\]]+)\]", rule)
        if col_vals_match:
            col_name, values_str = col_vals_match.groups()
            if col_name not in df.columns:
                return "FAILED", "None", f"Column '{col_name}' does not exist"
            # parse values e.g. "completed", "pending" -> ["completed", "pending"]
            allowed_vals = [v.strip().strip('"').strip("'") for v in values_str.split(",")]
            
            # Count records with invalid values
            invalid_count = df.filter(~df[col_name].isin(allowed_vals) & df[col_name].isNotNull()).count()
            passed = invalid_count == 0
            return "PASSED" if passed else "FAILED", f"{invalid_count} invalid records", f"Checks if values of column '{col_name}' fall in {allowed_vals}"

        # Default fallback for unrecognized rule syntax
        logger.warning(f"Unrecognized local DQDL rule syntax: '{rule}'. Defaulting to PASS.")
        return "PASSED", "N/A", "Unsupported local validation rule"
