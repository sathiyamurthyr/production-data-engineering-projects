"""
DQ Dashboard Generator Module.

Generates standalone, beautifully styled HTML quality dashboards from `QualityReport` execution results.
"""

import os
import logging
from typing import Optional
from src.dq_framework.quality_report import QualityReport
from src.dq_framework.quality_rule import Severity

logger = logging.getLogger(__name__)


class DQDashboard:
    """
    HTML Dashboard Generator for Data Quality Reports.
    """

    def __init__(self, template_title: str = "Enterprise Data Quality Dashboard"):
        self.template_title = template_title

    def generate(self, report: QualityReport, output_path: str = "quality_dashboard.html") -> str:
        """
        Generate standalone HTML quality report dashboard and save to file.

        Args:
            report: Executed QualityReport instance.
            output_path: Destination file path for generated HTML report.

        Returns:
            Absolute path to generated HTML dashboard file.
        """
        summary = report.summary_dict()
        
        status_color = "#28a745" if report.status == "PASSED" else ("#dc3545" if report.status == "FAILED" else "#ffc107")
        status_text_color = "#ffffff" if report.status != "WARNING" else "#000000"

        rule_rows_html = ""
        for r in report.results:
            badge_cls = "bg-success" if r.passed else ("bg-danger" if r.severity == Severity.CRITICAL or r.severity == Severity.ERROR else "bg-warning text-dark")
            status_badge = f'<span class="badge {badge_cls}">{"PASS" if r.passed else "FAIL"}</span>'
            sev_badge = f'<span class="badge bg-secondary">{r.severity.value}</span>'
            dim_badge = f'<span class="badge bg-info text-dark">{r.dimension.value}</span>'
            
            rule_rows_html += f"""
            <tr>
                <td>{status_badge}</td>
                <td><strong>{r.rule_name}</strong></td>
                <td>{dim_badge}</td>
                <td>{sev_badge}</td>
                <td>{r.passed_count} / {r.total_count}</td>
                <td>{r.failed_percentage:.2f}%</td>
                <td><small>{r.message}</small></td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.template_title} - {report.dataset_name}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        .header-banner {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 2rem 0; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .kpi-card {{ border-radius: 8px; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: transform 0.2s; }}
        .kpi-card:hover {{ transform: translateY(-2px); }}
        .kpi-value {{ font-size: 2.2rem; font-weight: 700; }}
        .kpi-label {{ text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px; color: #6c757d; }}
        .table-container {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .status-pill {{ background-color: {status_color}; color: {status_text_color}; padding: 0.4rem 1.2rem; border-radius: 50px; font-weight: 600; display: inline-block; }}
    </style>
</head>
<body>

    <div class="header-banner">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h2 class="mb-1">🔍 {self.template_title}</h2>
                    <p class="mb-0 text-light opacity-75">Dataset: <strong>{report.dataset_name}</strong> | Executed at: {report.execution_timestamp}</p>
                </div>
                <div>
                    <span class="status-pill">{report.status}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="container mb-4">
        <!-- KPI Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="card kpi-card p-3 text-center">
                    <div class="kpi-value text-primary">{report.total_records:,}</div>
                    <div class="kpi-label">Total Records</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi-card p-3 text-center">
                    <div class="kpi-value text-success">{report.overall_pass_rate:.1f}%</div>
                    <div class="kpi-label">Overall Pass Rate</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi-card p-3 text-center">
                    <div class="kpi-value text-info">{report.passed_rules} / {report.total_rules}</div>
                    <div class="kpi-label">Passed Rules</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card kpi-card p-3 text-center">
                    <div class="kpi-value text-danger">{report.failed_rules}</div>
                    <div class="kpi-label">Failed Rules</div>
                </div>
            </div>
        </div>

        <!-- Rule Evaluation Details Table -->
        <div class="table-container">
            <h4 class="mb-3 text-secondary">📋 Rule Execution Breakdown</h4>
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th>Status</th>
                            <th>Rule Name</th>
                            <th>Dimension</th>
                            <th>Severity</th>
                            <th>Pass / Total</th>
                            <th>Failure %</th>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rule_rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="mt-4 text-center text-muted small">
            Generated by Data Quality Engineering Framework • Sathiya Murthy | Data Engineering Diaries
        </footer>
    </div>

</body>
</html>
"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        abs_path = os.path.abspath(output_path)
        logger.info(f"Generated HTML Data Quality Dashboard at '{abs_path}'.")
        return abs_path
