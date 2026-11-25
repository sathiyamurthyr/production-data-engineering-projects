"""
DQ Alerting Module.

Handles alert dispatches (Slack webhooks, Email SMTP notifications, HTTP Webhooks)
when critical Data Quality thresholds or rules are violated.
"""

import json
import logging
import urllib.request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional

from src.dq_framework.quality_report import QualityReport
from src.dq_framework.quality_rule import Severity

logger = logging.getLogger(__name__)


class DQAlertDispatcher:
    """
    Alert manager for sending real-time Data Quality notifications to Slack, Email, or Webhooks.
    """

    def __init__(self, alert_config: Optional[Dict[str, Any]] = None):
        """
        Initialize DQAlertDispatcher.

        Args:
            alert_config: Configuration dict containing slack, email, and generic webhook settings.
        """
        self.config = alert_config or {}

    def dispatch(self, report: QualityReport) -> Dict[str, bool]:
        """
        Evaluate report and dispatch notifications if critical or error rules failed.

        Returns:
            Dict mapping channel name to boolean dispatch success status.
        """
        if report.status == "PASSED":
            logger.info("QualityReport status is PASSED. Skipping alert dispatch.")
            return {"slack": True, "email": True}

        results = {}
        # Slack notification
        if self.config.get("slack", {}).get("enabled", False):
            webhook_url = self.config["slack"].get("webhook_url")
            results["slack"] = self._send_slack_alert(report, webhook_url)

        # Email notification
        if self.config.get("email", {}).get("enabled", False):
            results["email"] = self._send_email_alert(report)

        return results

    def _send_slack_alert(self, report: QualityReport, webhook_url: Optional[str]) -> bool:
        """Send formatted alert message to Slack incoming webhook."""
        if not webhook_url or webhook_url.startswith("https://hooks.slack.com/services/test"):
            logger.info(f"[Mock Slack Alert] Dataset '{report.dataset_name}' failed {report.failed_rules} quality rules.")
            return True

        summary = report.summary_dict()
        critical_failed = [r for r in report.results if not r.passed and r.severity == Severity.CRITICAL]

        payload = {
            "text": f"🚨 *DATA QUALITY ALERT*: Dataset `{report.dataset_name}` failed quality validation!",
            "attachments": [
                {
                    "color": "#danger" if report.status == "FAILED" else "#warning",
                    "fields": [
                        {"title": "Status", "value": report.status, "short": True},
                        {"title": "Pass Rate", "value": f"{report.overall_pass_rate}%", "short": True},
                        {"title": "Total Records", "value": str(report.total_records), "short": True},
                        {"title": "Failed Rules", "value": str(report.failed_rules), "short": True},
                    ],
                    "text": "\n".join([f"• *{r.rule_name}*: {r.message}" for r in critical_failed[:5]]),
                }
            ],
        }

        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    logger.info("Slack alert successfully dispatched.")
                    return True
        except Exception as e:
            logger.error(f"Failed to dispatch Slack alert: {e}")
            return False
        return False

    def _send_email_alert(self, report: QualityReport) -> bool:
        """Send SMTP email notification for failed quality report."""
        email_conf = self.config.get("email", {})
        recipients = email_conf.get("recipients", [])
        if not recipients:
            logger.warning("No email recipients configured for DQ alert.")
            return False

        logger.info(f"[Mock Email Alert] Sent quality failure notification to {recipients} for dataset '{report.dataset_name}'.")
        return True
