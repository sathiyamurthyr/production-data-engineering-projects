import json
import logging
import requests
import smtplib
from email.mime.text import MIMEText
from src.orchestration.pipeline_config import PipelineConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class AlertingService:
    """Manages system alerts, handling Slack channel notifications and email dispatch."""

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.alert_cfg = self.config.alerting_config
        self.slack_url = self.alert_cfg.get("slack_webhook_url")
        self.email_settings = self.alert_cfg.get("email", {})

    def send_slack_alert(self, message: str, level: str = "INFO") -> bool:
        """Sends formatted warning or info payloads to Slack channels."""
        logger.info(f"Preparing Slack alert [Level: {level}]: {message}")

        # Choose emoji/formatting based on level
        color = "#36a64f"
        emoji = "ℹ️"
        if level == "WARNING":
            color = "#f2c612"
            emoji = "⚠️"
        elif level in ("ERROR", "CRITICAL"):
            color = "#ff0000"
            emoji = "🚨"

        payload = {
            "attachments": [
                {
                    "fallback": f"[{level}] {message}",
                    "color": color,
                    "title": f"{emoji} DataMart Global Alert - {level}",
                    "text": message,
                    "mrkdwn_in": ["text"]
                }
            ]
        }

        # Check if URL looks like a real Slack webhook URL
        if not self.slack_url or "hooks.slack.com" not in self.slack_url:
            logger.info(f"[SIMULATED SLACK DISPATCH] Webhook URL not set. Payload:\n{json.dumps(payload, indent=2)}")
            return True

        try:
            res = requests.post(self.slack_url, json=payload, timeout=5)
            if res.status_code == 200:
                logger.info("Slack alert successfully transmitted.")
                return True
            else:
                logger.error(f"Slack post failed. Status code: {res.status_code}, Response: {res.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to post Slack notification: {e}")
            return False

    def send_email_alert(self, subject: str, body: str) -> bool:
        """Dispatches an email alert using configured SMTP servers."""
        sender = self.email_settings.get("sender", "data-alerts@datamart.com")
        recipients = self.email_settings.get("recipients", ["oncall-de@datamart.com"])
        smtp_server = self.email_settings.get("smtp_server", "smtp.example.com")
        smtp_port = self.email_settings.get("smtp_port", 587)

        msg = MIMEText(body)
        msg["Subject"] = f"DataMart Global System Alert: {subject}"
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)

        logger.info(f"Preparing email alert: '{subject}' to {recipients}")

        # Simulate or dispatch SMTP
        if smtp_server == "smtp.example.com":
            logger.info(f"[SIMULATED SMTP DISPATCH] To: {recipients}\nSubject: {subject}\nBody:\n{body}")
            return True

        try:
            smtp_pwd = os.environ.get("SMTP_PASSWORD", "")
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if smtp_pwd:
                    server.login(sender, smtp_pwd)
                server.sendmail(sender, recipients, msg.as_string())
            logger.info("Email alert successfully sent.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

if __name__ == "__main__":
    alert = AlertingService()
    alert.send_slack_alert("Capstone Pipeline run initiated.", "INFO")
    alert.send_slack_alert("Data Quality validation failed on Silver orders.", "WARNING")
