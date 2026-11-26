import logging
from pathlib import Path
import pandas as pd
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ExecutiveReportGenerator:
    """Queries Gold tables to compile executive performance reports and formatted dashboards."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.gold_path = Path(self.config.storage_config.get("gold_path"))
        self.reports_dir = Path(self.config.storage_config.get("base_path")) / "reports"

    def _read_dataset(self, dataset_name: str) -> pd.DataFrame:
        """Reads dataset from Gold layer using the fallback loading utility."""
        target_dir = self.gold_path / dataset_name
        return bronze_utils.load_fallback_df(target_dir)

    def _format_table(self, df: pd.DataFrame) -> str:
        """Formats DataFrame as a markdown table using tabulate or custom fallback."""
        if HAS_TABULATE:
            return tabulate(df, headers="keys", tablefmt="github", showindex=False)
        else:
            # Custom markdown table generator
            cols = list(df.columns)
            headers_line = "| " + " | ".join(cols) + " |"
            sep_line = "| " + " | ".join(["---"] * len(cols)) + " |"
            rows_lines = []
            for _, r in df.iterrows():
                rows_lines.append("| " + " | ".join([str(r[c]) for c in cols]) + " |")
            return "\n".join([headers_line, sep_line] + rows_lines)

    def generate_report(self) -> str:
        logger.info("Generating executive metrics report...")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # 1. Load Data
        df_cat = self._read_dataset("sales_analytics/category_sales")
        df_daily = self._read_dataset("sales_analytics/daily_sales")
        df_marketing = self._read_dataset("marketing_metrics")

        # 2. Compile Report Contents
        report_lines = []
        report_lines.append("# DataMart Global - Executive Performance Report")
        report_lines.append("## Platform Metrics Dashboard\n")

        # Category Sales Table
        if not df_cat.empty:
            report_lines.append("### Sales performance by Product Category")
            cat_table = self._format_table(df_cat)
            report_lines.append(cat_table + "\n")
        else:
            report_lines.append("_Category sales data unavailable._\n")

        # Daily Revenue Trend
        if not df_daily.empty:
            report_lines.append("### Daily Net Revenue Trends")
            daily_table = self._format_table(df_daily)
            report_lines.append(daily_table + "\n")
        else:
            report_lines.append("_Daily revenue trend data unavailable._\n")

        # Marketing Conversion rates
        if not df_marketing.empty:
            report_lines.append("### Customer Interactions and Clickstream Conversions")
            mkt_table = self._format_table(df_marketing)
            report_lines.append(mkt_table + "\n")
        else:
            report_lines.append("_Marketing engagement metrics unavailable._\n")

        report_content = "\n".join(report_lines)

        # Write to reports folder
        target_report = self.reports_dir / "executive_report.md"
        with open(target_report, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"Executive report generated successfully at: {target_report}")
        
        print("\n=== SYSTEM REPORT GENERATION ===")
        print(report_content)
        print("================================\n")
        
        return str(target_report)

if __name__ == "__main__":
    cfg = PipelineConfig()
    generator = ExecutiveReportGenerator(cfg)
    generator.generate_report()
