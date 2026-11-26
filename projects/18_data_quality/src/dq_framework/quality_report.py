from typing import Dict, List, Any, Optional
import json
import datetime
from src.dq_framework.quality_rule import RuleResult, Severity

class QualityReport:
    """
    Consolidates the metrics, details, and results of a validation execution.
    Can export summaries as dictionaries, JSON strings, or print reports.
    """

    def __init__(
        self,
        dataset_name: Optional[str] = None,
        table_name: Optional[str] = None,
        total_records: int = 0,
        results: Optional[List[RuleResult]] = None,
        execution_duration_seconds: float = 0.05
    ):
        self.dataset_name = dataset_name or table_name or "dataset"
        self.table_name = self.dataset_name
        self.total_records = total_records
        self.passed_records = 0
        self.quarantined_records = 0
        self.rule_results: List[RuleResult] = results or []
        self.status = "PASSED"  # FAILED if any CRITICAL or ERROR rule fails
        
        # If results are passed, we evaluate status
        if results:
            for r in results:
                if not r.passed and r.severity in [Severity.ERROR, Severity.CRITICAL, "ERROR", "CRITICAL"]:
                    self.status = "FAILED"
                    
        self.execution_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.execution_duration_seconds = execution_duration_seconds

    @property
    def total_rules(self) -> int:
        return len(self.rule_results)

    @property
    def failed_rules(self) -> int:
        return sum(1 for r in self.rule_results if not r.passed)

    @property
    def passed_rules(self) -> int:
        return sum(1 for r in self.rule_results if r.passed)

    @property
    def results(self) -> List[RuleResult]:
        return self.rule_results

    @property
    def overall_pass_rate(self) -> float:
        if self.total_records > 0:
            return round((self.passed_records / self.total_records) * 100, 2)
        return 100.0

    def add_rule_result(self, result: RuleResult):
        """Adds validation details for a single rule check."""
        self.rule_results.append(result)
        
        # If an error or critical level rule fails, update overall status to FAILED
        if not result.passed and result.severity in [Severity.ERROR, Severity.CRITICAL, "ERROR", "CRITICAL"]:
            self.status = "FAILED"

    def finalize(self, passed_count: int, quarantined_count: int):
        """Finalizes the aggregate counts for the run."""
        self.passed_records = passed_count
        self.quarantined_records = quarantined_count

    def summary_dict(self) -> Dict[str, Any]:
        """Returns a summary dictionary formatted for tracker and monitoring tools."""
        crit_count = sum(1 for r in self.rule_results if not r.passed and r.severity in [Severity.CRITICAL, "CRITICAL"])
        err_count = sum(1 for r in self.rule_results if not r.passed and r.severity in [Severity.ERROR, "ERROR"])
        warn_count = sum(1 for r in self.rule_results if not r.passed and r.severity in [Severity.WARNING, "WARNING"])
        
        return {
            "dataset_name": self.dataset_name,
            "status": self.status,
            "total_records": self.total_records,
            "passed_records": self.passed_records,
            "quarantined_records": self.quarantined_records,
            "overall_pass_rate": self.overall_pass_rate,
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "severity_failures": {
                "CRITICAL": crit_count,
                "ERROR": err_count,
                "WARNING": warn_count
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert the report to a dictionary representation."""
        rule_details = []
        for r in self.rule_results:
            rule_details.append(r.to_dict())
            
        return {
            "dataset_name": self.dataset_name,
            "total_records": self.total_records,
            "passed_records": self.passed_records,
            "quarantined_records": self.quarantined_records,
            "status": self.status,
            "pass_rate_pct": self.overall_pass_rate,
            "total_rules": self.total_rules,
            "failed_rules": self.failed_rules,
            "rule_details": rule_details
        }

    def to_json(self, indent: int = 4) -> str:
        """Convert the report to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def print_summary(self):
        """Prints a clean CLI-friendly text summary of the quality report."""
        summary = self.to_dict()
        print("=" * 60)
        print(f"DATA QUALITY REPORT: {summary['dataset_name'].upper()}")
        print("=" * 60)
        print(f"Execution Status    : {summary['status']}")
        print(f"Total Rows Checked  : {summary['total_records']}")
        print(f"Passed Rows         : {summary['passed_records']} ({summary['pass_rate_pct']}%)")
        print(f"Quarantined Rows     : {summary['quarantined_records']}")
        print(f"Total Rules Run     : {summary['total_rules']}")
        print(f"Rules Failed        : {summary['failed_rules']}")
        print("-" * 60)
        print("RULE EXECUTION DETAILS:")
        for rule in summary["rule_details"]:
            status_str = "PASS" if rule["passed"] else f"FAIL ({rule['failed_count']} rows)"
            print(f"  - [{rule['severity']}][{rule['dimension']}] {rule['rule_name']} -> {status_str}")
            if not rule["passed"]:
                print(f"    Failed Indices (max 10): {rule['failed_indices']}")
        print("=" * 60)
