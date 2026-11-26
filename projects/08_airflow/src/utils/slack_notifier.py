"""
Utility: slack_notifier.py
===========================

PURPOSE:
    Production Slack alerting callbacks for Apache Airflow DAGs.
    Constructs formatted Slack messages containing failure stack traces, DAG metadata,
    execution dates, retry attempt counts, and direct links to Airflow task logs.

CONCEPTS COVERED:
    1. `on_failure_callback`, `on_success_callback`, and `sla_miss_callback` hooks
    2. Parsing execution context dictionary safely
    3. Slack Webhook / REST API integration using Airflow Connections (`slack_webhook_default`)
    4. Graceful error handling (alerts must not break DAG execution)

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import requests

from airflow.hooks.base import BaseHook

log = logging.getLogger(__name__)

SLACK_CONN_ID = "slack_webhook_default"


def _send_slack_message(webhook_url: str, payload: Dict[str, Any]) -> bool:
    """
    Sends payload to Slack Webhook URL.
    """
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            log.info("Slack notification dispatched successfully.")
            return True
        else:
            log.warning("Slack Webhook returned HTTP %d: %s", response.status_code, response.text)
            return False
    except Exception as err:
        log.error("Failed to post Slack notification: %s", str(err))
        return False


def get_slack_webhook_url() -> str:
    """
    Retrieves Slack Webhook URL from Airflow Connections or returns a fallback mock URL.
    """
    try:
        conn = BaseHook.get_connection(SLACK_CONN_ID)
        # Webhook URL is often stored in host or password or extra
        if conn.host and conn.host.startswith("http"):
            return conn.host
        elif conn.extra_dejson.get("webhook_url"):
            return conn.extra_dejson["webhook_url"]
        return "https://hooks.slack.com/services/MOCK/WEBHOOK/URL"
    except Exception:
        log.info("Slack connection '%s' not configured. Using fallback log notification.", SLACK_CONN_ID)
        return "https://hooks.slack.com/services/MOCK/WEBHOOK/URL"


def slack_fail_alert(context: Dict[str, Any]) -> None:
    """
    Callback function assigned to `on_failure_callback` on tasks or DAGs.
    """
    ti = context.get("task_instance")
    dag_id = ti.dag_id if ti else "Unknown_DAG"
    task_id = ti.task_id if ti else "Unknown_Task"
    execution_date = context.get("ds", "Unknown_Date")
    exception = context.get("exception", "No explicit exception detail")
    try_number = ti.try_number if ti else 1
    log_url = ti.log_url if ti else "N/A"

    payload = {
        "text": f"🚨 *Airflow Task Failure Alert* - `{dag_id}`",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Task Failure Alert",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*DAG ID:*\n`{dag_id}`"},
                    {"type": "mrkdwn", "text": f"*Task ID:*\n`{task_id}`"},
                    {"type": "mrkdwn", "text": f"*Execution Date:*\n`{execution_date}`"},
                    {"type": "mrkdwn", "text": f"*Try Count:*\n`{try_number}`"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Exception Details:*\n```\n{str(exception)[:500]}\n```",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔗 <{log_url}|View Airflow Task Log>",
                },
            },
        ],
    }

    webhook_url = get_slack_webhook_url()
    _send_slack_message(webhook_url, payload)


def slack_success_alert(context: Dict[str, Any]) -> None:
    """
    Callback function assigned to `on_success_callback` on tasks or DAGs.
    """
    ti = context.get("task_instance")
    dag_id = ti.dag_id if ti else "Unknown_DAG"
    execution_date = context.get("ds", "Unknown_Date")
    duration = round(ti.duration, 2) if ti and ti.duration else 0.0

    payload = {
        "text": f"✅ *Airflow Pipeline Success* - `{dag_id}` completed in {duration}s for {execution_date}",
    }

    webhook_url = get_slack_webhook_url()
    _send_slack_message(webhook_url, payload)


def slack_sla_miss_alert(dag, task_list, blocking_task_list, slas, blocking_tis) -> None:
    """
    Callback function assigned to `sla_miss_callback` on DAG definition.
    """
    dag_id = dag.dag_id
    payload = {
        "text": f"⏱️ *Airflow SLA Miss Alert* - DAG `{dag_id}` missed SLA deadline for tasks: `{task_list}`",
    }

    webhook_url = get_slack_webhook_url()
    _send_slack_message(webhook_url, payload)
