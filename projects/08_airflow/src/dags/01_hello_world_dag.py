"""
DAG: 01_hello_world_dag.py
==========================

PURPOSE:
    Introductory DAG demonstrating the foundational building blocks of Apache Airflow.
    This is the "Hello, World!" of Airflow — every data engineer should understand
    every line of this file before moving on to more complex patterns.

CONCEPTS COVERED:
    1. DAG object: The container that defines a workflow
    2. default_args: Shared arguments applied to all tasks in the DAG
    3. Schedule interval: cron expressions, presets, and timedelta
    4. Operators: BashOperator, PythonOperator, EmptyOperator
    5. Task dependencies: set_upstream / set_downstream / bitshift operators
    6. XCom (cross-communication): Sharing values between tasks

BUSINESS USE CASE:
    Morning data pipeline health check — a lightweight DAG that verifies the Airflow
    environment is responsive, logs a greeting with execution metadata, and signals
    downstream systems. Runs daily at 06:00 UTC.

DAG FLOW:
    start >> print_date >> [greet_task, env_check] >> end

EXPECTED BEHAVIOR:
    - Scheduled: daily at 06:00 UTC (catchup=False means no backfill on first run)
    - Tasks run sequentially or in parallel as defined
    - XCom pushes greeting message visible in the Airflow UI

PERFORMANCE NOTES:
    - EmptyOperator has near-zero overhead — use it as start/end sentinels
    - PythonOperator tasks run in the scheduler's worker process by default
    - Keep callable functions lightweight; heavy work belongs in Spark/dbt/external systems

COMMON MISTAKES:
    1. Forgetting to set catchup=False on new DAGs (causes backfill storms)
    2. Putting heavy computation inside PythonOperator callables
    3. Using mutable default arguments in default_args
    4. Not setting a start_date (DAG will not schedule)
    5. Using datetime.now() as start_date (always use a fixed past date)

INTERVIEW QUESTIONS:
    Q: What is a DAG in Airflow?
    A: A Directed Acyclic Graph — a collection of tasks with defined dependencies,
       no cycles allowed. It represents a workflow to be executed.

    Q: What is the difference between schedule_interval and timetable?
    A: schedule_interval uses cron/timedelta strings (legacy), while timetable is the
       modern Airflow 2.2+ API allowing custom scheduling logic (e.g., business days).

    Q: What does catchup=False do?
    A: Prevents Airflow from backfilling all missed DAG runs between start_date and now.
       Without it, a new DAG with a start_date 1 year ago would trigger 365 runs.

    Q: What is an Execution Date?
    A: The logical time period a DAG run represents. For a daily DAG running on 2024-01-02,
       the execution_date is 2024-01-01 (the start of the interval it covers).

    Q: How does XCom work?
    A: Tasks push values to Airflow's metadata database via xcom_push(). Other tasks
       pull these values using xcom_pull(task_ids='source_task'). XCom is NOT for large
       data — use S3/GCS paths as pointers instead.

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import logging
import os
import platform
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

# ---------------------------------------------------------------------------
# Logger — use Airflow's logger, not print() in production
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DEFAULT ARGS
# Applied to every task in the DAG unless a task overrides them.
# Think of default_args as the "base configuration" for all tasks.
# ---------------------------------------------------------------------------
default_args: dict = {
    # Owner shows up in the Airflow UI and is used for filtering
    "owner": "data-engineering-diaries",

    # Whether to send email on task failure (requires SMTP config in airflow.cfg)
    "email_on_failure": False,
    "email_on_retry": False,

    # Recipients for alert emails (list of strings)
    "email": ["data-team@company.com"],

    # Number of times Airflow retries a failed task before marking it FAILED
    "retries": 1,

    # Wait between retries — exponential backoff is also supported
    "retry_delay": timedelta(minutes=5),

    # If a task doesn't finish within this time, mark it as FAILED
    # "execution_timeout": timedelta(hours=1),

    # SLA: Trigger an SLA miss alert if the task hasn't completed by this deadline
    # "sla": timedelta(hours=2),
}

# ---------------------------------------------------------------------------
# CALLABLE FUNCTIONS for PythonOperator
# ---------------------------------------------------------------------------

def greet(**context: dict) -> str:
    """
    Print a greeting and demonstrate how to access Airflow context variables.

    The **context dict is injected by Airflow when provide_context=True (pre-2.0)
    or automatically in Airflow 2.x. It contains metadata about the current run:
      - context['ds']:          execution date as string 'YYYY-MM-DD'
      - context['ds_nodash']:   execution date without dashes 'YYYYMMDD'
      - context['execution_date']: pendulum datetime object
      - context['dag']:         the DAG object
      - context['task']:        the current task object
      - context['run_id']:      unique run identifier
      - context['ti']:          TaskInstance object (for XCom push/pull)

    Returns:
        str: The greeting message (also pushed to XCom automatically when returned)
    """
    # Access context variables
    execution_date: str = context["ds"]
    run_id: str = context["run_id"]
    dag_id: str = context["dag"].dag_id

    message = (
        f"Hello from DAG '{dag_id}'! "
        f"Execution date: {execution_date} | Run ID: {run_id}"
    )
    log.info(message)

    # Explicitly push to XCom (returning from a PythonOperator also auto-pushes
    # to key='return_value' in Airflow 2.x)
    context["ti"].xcom_push(key="greeting_message", value=message)

    return message


def check_environment(**context: dict) -> None:
    """
    Validate that the Airflow worker environment meets minimum requirements.
    In production, this would check: Python version, installed packages,
    disk space, memory availability, and connectivity to critical services.
    """
    python_version: str = platform.python_version()
    hostname: str = platform.node()
    os_name: str = platform.system()

    log.info("=== Environment Check ===")
    log.info("Python version : %s", python_version)
    log.info("Hostname       : %s", hostname)
    log.info("OS             : %s", os_name)
    log.info("AIRFLOW_HOME   : %s", os.getenv("AIRFLOW_HOME", "Not set"))

    # Validate Python version >= 3.10
    major, minor, *_ = python_version.split(".")
    if int(major) < 3 or (int(major) == 3 and int(minor) < 10):
        raise ValueError(
            f"Python 3.10+ required, found {python_version}. "
            "Upgrade your worker image."
        )

    log.info("Environment check PASSED.")


def pull_and_log_greeting(**context: dict) -> None:
    """
    Demonstrate XCom pull — retrieve the greeting pushed by greet_task
    and log it. Shows how tasks communicate through Airflow's metadata DB.
    """
    # Pull from a specific task's XCom by task_id and key
    greeting: str | None = context["ti"].xcom_pull(
        task_ids="greet_task",
        key="greeting_message",
    )
    log.info("Pulled greeting via XCom: %s", greeting)

    if not greeting:
        log.warning("No greeting found in XCom — greet_task may have failed.")


# ---------------------------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------------------------
with DAG(
    dag_id="01_hello_world",
    description="Introductory DAG: DAG structure, default_args, schedule, XCom basics",
    default_args=default_args,

    # -----------------------------------------------------------------------
    # START DATE: Must be a fixed past datetime, never datetime.now()
    # Airflow uses this to calculate the first scheduled run.
    # The first run fires at start_date + schedule_interval.
    # -----------------------------------------------------------------------
    start_date=datetime(2024, 1, 1),

    # -----------------------------------------------------------------------
    # SCHEDULE: When to run the DAG
    #   Cron presets : @daily, @hourly, @weekly, @monthly, @once
    #   Cron strings : "0 6 * * *" (6 AM UTC daily)
    #   timedelta    : timedelta(hours=6)
    #   None         : Manual runs only
    # -----------------------------------------------------------------------
    schedule="0 6 * * *",  # Daily at 06:00 UTC

    # -----------------------------------------------------------------------
    # CATCHUP: False = only run the most recent missed interval, not all missed ones
    # Set to True for backfill-required pipelines (e.g., historical data loads)
    # -----------------------------------------------------------------------
    catchup=False,

    # -----------------------------------------------------------------------
    # TAGS: Categorize DAGs in the Airflow UI for filtering
    # -----------------------------------------------------------------------
    tags=["tutorial", "hello-world", "data-engineering-diaries"],

    # -----------------------------------------------------------------------
    # MAX ACTIVE RUNS: Prevent multiple concurrent executions of this DAG
    # Especially important for DAGs that write to shared resources
    # -----------------------------------------------------------------------
    max_active_runs=1,

    # -----------------------------------------------------------------------
    # DOC MD: Rendered as documentation in the Airflow UI's DAG detail page
    # -----------------------------------------------------------------------
    doc_md="""
## Hello World DAG

This DAG demonstrates foundational Airflow concepts:
- **DAG** structure and `default_args`
- **Scheduling** with cron expressions
- **BashOperator** and **PythonOperator**
- **XCom** for inter-task communication
- **Task dependencies** with bitshift operators

**Schedule**: Daily at 06:00 UTC  
**Owner**: data-engineering-diaries
    """,
) as dag:

    # -----------------------------------------------------------------------
    # TASK 1: Start sentinel
    # EmptyOperator (formerly DummyOperator) — zero-work task used as a
    # logical entry/exit point. Great for grouping task dependencies.
    # -----------------------------------------------------------------------
    start = EmptyOperator(
        task_id="start",
        doc_md="Pipeline entry point. No work performed.",
    )

    # -----------------------------------------------------------------------
    # TASK 2: BashOperator — run a shell command
    # Useful for: calling CLI tools, running scripts, invoking dbt, etc.
    # The bash_command string is passed to bash -c "..."
    # -----------------------------------------------------------------------
    print_date = BashOperator(
        task_id="print_date",
        bash_command="echo 'Airflow execution date: {{ ds }}' && date",
        # Jinja templating: {{ ds }} is rendered to the execution date string
        # Other useful template variables:
        #   {{ ds_nodash }}        → 'YYYYMMDD'
        #   {{ execution_date }}   → full datetime
        #   {{ next_ds }}          → next execution date
        #   {{ prev_ds }}          → previous execution date
        #   {{ dag.dag_id }}       → DAG id string
        #   {{ var.value.my_var }} → Airflow Variable value
        doc_md="Print the Airflow execution date using Jinja templating.",
    )

    # -----------------------------------------------------------------------
    # TASK 3: PythonOperator — run a Python callable
    # python_callable: any Python function
    # op_kwargs: keyword arguments passed to the callable
    # -----------------------------------------------------------------------
    greet_task = PythonOperator(
        task_id="greet_task",
        python_callable=greet,
        # op_kwargs={"custom_key": "custom_value"},  # pass extra args
        doc_md="Push a greeting message to XCom and log environment metadata.",
    )

    # -----------------------------------------------------------------------
    # TASK 4: Environment check (runs in parallel with greet_task)
    # -----------------------------------------------------------------------
    env_check = PythonOperator(
        task_id="env_check",
        python_callable=check_environment,
        doc_md="Validate Python version and environment variables on the worker.",
    )

    # -----------------------------------------------------------------------
    # TASK 5: Pull and log greeting from XCom (runs after greet_task)
    # -----------------------------------------------------------------------
    log_greeting = PythonOperator(
        task_id="log_greeting",
        python_callable=pull_and_log_greeting,
        doc_md="Demonstrate XCom pull by retrieving the greeting from greet_task.",
    )

    # -----------------------------------------------------------------------
    # TASK 6: End sentinel
    # -----------------------------------------------------------------------
    end = EmptyOperator(
        task_id="end",
        doc_md="Pipeline exit point. All tasks completed successfully.",
    )

    # -----------------------------------------------------------------------
    # TASK DEPENDENCIES
    # Three equivalent ways to express the same dependency:
    #
    # 1. Bitshift (most common, readable):
    #    start >> print_date >> [greet_task, env_check] >> end
    #
    # 2. set_downstream / set_upstream:
    #    start.set_downstream(print_date)
    #    print_date.set_downstream([greet_task, env_check])
    #
    # 3. chain() utility (good for long linear chains):
    #    from airflow.models.baseoperator import chain
    #    chain(start, print_date, [greet_task, env_check], end)
    # -----------------------------------------------------------------------

    # Linear: start → print_date
    start >> print_date

    # Fan-out: print_date → greet_task AND env_check (parallel execution)
    print_date >> [greet_task, env_check]

    # greet_task → log_greeting (sequential — must run after greet)
    greet_task >> log_greeting

    # Fan-in: both log_greeting and env_check → end
    [log_greeting, env_check] >> end
