import logging
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
from src.dq_framework.quality_rule import QualityRule, Severity, Dimension, RuleResult
from src.dq_framework.rule_registry import RuleRegistry
from src.dq_framework.quality_report import QualityReport

logger = logging.getLogger(__name__)

class QualityEngine:
    """
    The orchestrator that parses configurations, instantiates validation rules,
    runs them against incoming datasets, separates clean from quarantined data,
    and returns a structured validation report.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        rules: Optional[List[QualityRule]] = None,
        dataset_name: str = "dataset"
    ):
        self.config = config or {}
        self.rules = rules or []
        self.dataset_name = dataset_name

    def build_rules(self, table_name: str) -> List[QualityRule]:
        """
        Parses configuration and instantiates the registered QualityRule objects.
        
        Args:
            table_name (str): Name of the dataset table.
            
        Returns:
            List[QualityRule]: Instantiated quality rules.
        """
        table_config = self.config.get("datasets", {}).get(table_name)
        if not table_config:
            raise ValueError(f"Table '{table_name}' configuration not found in dq_config.yaml")

        rules_config = table_config.get("rules", [])
        rules_list = []

        for rule_cfg in rules_config:
            rule_type = rule_cfg.get("rule_type")
            column = rule_cfg.get("column")
            severity_str = rule_cfg.get("severity", "ERROR")
            description = rule_cfg.get("description", "")

            # Convert severity string to Severity Enum
            try:
                severity = Severity[severity_str.upper()]
            except KeyError:
                severity = Severity.ERROR

            # Extract any rule-specific keyword arguments (like regex, allowed_values, min/max values)
            kwargs = {k: v for k, v in rule_cfg.items() if k not in ["rule_type", "column", "severity", "description"]}

            try:
                # Get the specific registered rule subclass
                rule_class = RuleRegistry.get_rule_class(rule_type)
                rule_instance = rule_class(
                    column=column,
                    severity=severity,
                    description=description,
                    **kwargs
                )
                rules_list.append(rule_instance)
            except Exception as e:
                logger.error(f"Failed to build rule of type '{rule_type}' for column '{column}': {str(e)}")
                raise e

        return rules_list

    def run(self, df: pd.DataFrame) -> QualityReport:
        """
        Runs validation rules against the DataFrame and returns a QualityReport.
        """
        report = QualityReport(dataset_name=self.dataset_name, total_records=len(df))
        for rule in self.rules:
            try:
                result = rule.evaluate(df)
                report.add_rule_result(result)
            except Exception as e:
                logger.exception(f"Error evaluating rule {rule.name}: {e}")
                # Create a failed rule result for safety
                failed_res = RuleResult(
                    rule_name=rule.name,
                    dimension=getattr(rule, "dimension", Dimension.COMPLETENESS),
                    passed=False,
                    failed_count=len(df),
                    passed_count=0,
                    failed_indices=df.index.tolist(),
                    details={"error": str(e)},
                    severity=rule.severity
                )
                report.add_rule_result(failed_res)
        return report

    def partition_data(self, df: pd.DataFrame, report: QualityReport) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Partitions the input DataFrame into clean (passed) and quarantined data
        based on the evaluation results of rules with severity ERROR or CRITICAL.
        """
        # Collect indices of rows that failed any rule with ERROR or CRITICAL severity
        failed_indices_set = set()
        for result in report.rule_results:
            if not result.passed and result.severity in [Severity.ERROR, Severity.CRITICAL, "ERROR", "CRITICAL"]:
                failed_indices_set.update(result.failed_indices)

        quarantine_mask = df.index.isin(failed_indices_set)
        
        clean_df = df[~quarantine_mask].copy()
        quarantine_df = df[quarantine_mask].copy()
        
        report.finalize(passed_count=len(clean_df), quarantined_count=len(quarantine_df))
        
        return clean_df, quarantine_df

    def validate_dataset(self, table_name: str, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, QualityReport]:
        """
        Runs validation rules against the DataFrame and splits into passed and quarantined data
        based on the config.
        
        Args:
            table_name (str): Name of the dataset.
            df (pd.DataFrame): DataFrame to validate.
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, QualityReport]: 
                Passed DataFrame, Quarantined DataFrame, and the final QualityReport object.
        """
        self.rules = self.build_rules(table_name)
        self.dataset_name = table_name

        report = self.run(df)
        passed_df, quarantined_df = self.partition_data(df, report)

        return passed_df, quarantined_df, report
