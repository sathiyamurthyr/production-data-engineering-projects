# Enterprise Apache Airflow Interview Questions & Answers

This document provides 25+ comprehensive scenario-based and technical interview questions for Data Engineering candidates targeting Senior/Staff Data Architect roles.

---

## Category 1: Core Concepts & Architecture

### Q1: Can you explain the internal execution flow when a DAG is triggered in Airflow?
**Answer**:
1. **DAG Parsing**: The `DagFileProcessor` parses the Python DAG file in `$AIRFLOW_HOME/dags` and serializes the DAG structure into the `serialized_dag` metadata table.
2. **DAG Run Creation**: The Scheduler identifies that a DAG's schedule timetable criteria is satisfied, or a manual trigger is requested. It creates a `DagRun` entry in state `QUEUED` -> `RUNNING`.
3. **Task Instance Scheduling**: The Scheduler evaluates task dependencies (`TaskInstance` state). When upstream dependencies pass, the task state is set to `SCHEDULED`.
4. **Executor Queuing**: The Scheduler transitions the task to `QUEUED` and publishes the task payload to the Executor queue (e.g. Redis for `CeleryExecutor`).
5. **Worker Execution**: An Airflow Worker process pops the task message from the queue, sets task state to `RUNNING`, executes the python callable / operator, and updates task state in the metadata DB to `SUCCESS` or `FAILED`.
6. **Callbacks & Downstream Triggering**: If configured, `on_success_callback` or `on_failure_callback` fires. The Scheduler discovers the state change and evaluates downstream tasks.

### Q2: What is the difference between `execution_date`, `logical_date`, and `data_interval_start` in Airflow 2.x?
**Answer**:
In Airflow 2.2+, `execution_date` was renamed to `logical_date` to reduce confusion.
- `logical_date` / `execution_date` represents the start of the data interval that the DAG run is processing, **NOT** the wall-clock time when the DAG actually starts running.
- For a daily DAG configured for `0 0 * * *`:
  - `data_interval_start`: `2024-01-01 00:00:00`
  - `data_interval_end`: `2024-01-02 00:00:00`
  - `logical_date`: `2024-01-01 00:00:00`
  - Actual Run Start Time: `2024-01-02 00:00:05` (triggered immediately after the interval completes).

### Q3: What is `catchup=False` and why is it crucial in production?
**Answer**:
When `catchup=True` (the default in older Airflow versions), Airflow will trigger a `DagRun` for **every** missed schedule interval between the DAG's `start_date` and the current date when a DAG is unpaused. If `start_date` is 1 year ago for a daily DAG, Airflow will immediately queue 365 concurrent DAG runs, causing a "backfill storm" that can crash database pools and external APIs.  
Setting `catchup=False` instructs Airflow to only trigger the most recent schedule interval.

---

## Category 2: TaskFlow API, Operators & Hooks

### Q4: How does TaskFlow API handle XCom serialization under the hood?
**Answer**:
In TaskFlow API (`@task`), returning a value from a decorated function automatically pushes it to XCom under the key `"return_value"`. Passing that returned object as an argument to another `@task` function causes Airflow to implicitly resolve `xcom_pull(task_ids='source_task', key='return_value')`.  
Airflow uses `XComArg` objects to construct the DAG dependency graph dynamically during parsing.

### Q5: How do you implement Dynamic Task Mapping (`.expand()`) and what are its limits?
**Answer**:
Dynamic Task Mapping (`.expand()`) creates task instances at runtime based on the length of a list:
```python
@task
def get_files():
    return ["file_a.csv", "file_b.csv", "file_c.csv"]

@task
def process_file(filename: str):
    print(f"Processing {filename}")

files = get_files()
process_file.expand(filename=files)  # Creates 3 mapped task instances
```
**Limits**: Default max mapped instances is 1,024 (`max_map_length` setting). Mapping over tens of thousands of items should be chunked to prevent metadata DB write locks.

---

## Category 3: Data-Aware Scheduling & Sensors

### Q6: Contrast Data-Aware Scheduling (`Dataset`) with `ExternalTaskSensor`.
**Answer**:
- **`ExternalTaskSensor`**: Polling-based dependency. Tightly coupled to an upstream DAG ID and specific execution time. Requires worker process or reschedule polling cycles.
- **`Dataset`**: Event-driven architecture. Upstream tasks declare `outlets=[Dataset("s3://bucket/key")]`. Downstream DAGs specify `schedule=[Dataset("s3://bucket/key")]`. The downstream DAG triggers instantly when the dataset event is emitted by the scheduler, regardless of cron schedules.

### Q7: Explain `poke` mode vs `reschedule` mode in Airflow Sensors.
**Answer**:
- **`poke` mode**: The sensor task holds its worker slot continuously, sleeping for `poke_interval` seconds in a loop until the condition is met or timeout occurs. Wastes worker capacity for long waits.
- **`reschedule` mode**: Upon evaluating the condition as `False`, the sensor task frees up its worker process slot, sets state to `up_for_reschedule`, and re-queues itself after `poke_interval` seconds.

---

## Category 4: Error Handling & Resilience

### Q8: How do you design a Dead Letter Queue (DLQ) pattern in Airflow?
**Answer**:
Use `TriggerRule.ONE_FAILED` on a dedicated cleanup/isolation task:
```python
dlq_task = PythonOperator(
    task_id="dlq_handler",
    python_callable=isolate_failed_records,
    trigger_rule=TriggerRule.ONE_FAILED,
)
processing_task >> [normal_end, dlq_task]
```
If `processing_task` fails after all retries, `dlq_task` executes, extracting error details from XCom / logs and writing the unprocessable payload metadata to a database table or S3 bucket for manual auditing.

### Q9: How do you configure exponential backoff retries in Airflow?
**Answer**:
Set retry parameters in `default_args`:
```python
default_args = {
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "retry_exponential_backoff": True,  # Delays: 30s -> 60s -> 120s
    "max_retry_delay": timedelta(minutes=10),
}
```

---

## Category 5: Performance & Scaling

### Q10: Why should you avoid top-level code execution in DAG files?
**Answer**:
The Airflow Scheduler continuously executes every Python file in `$AIRFLOW_HOME/dags` to parse DAG definitions (default frequency: every 30 seconds). Any top-level SQL query, HTTP API call, or heavy calculation will run on EVERY parse cycle, clogging CPU cores, exhausting connection pools, and delaying DAG scheduling across the cluster.


---

### Q11: Compare `LocalExecutor`, `CeleryExecutor`, and `KubernetesExecutor` in Airflow.
**Answer**:
- **`LocalExecutor`:** Runs tasks as parallel subprocesses on the Scheduler/single host; simple for dev/small setups, does not scale horizontally.
- **`CeleryExecutor`:** Distributes tasks via Redis/RabbitMQ to a fleet of persistent worker nodes; fast task startup, ideal for steady high-volume workloads.
- **`KubernetesExecutor`:** Spins up an isolated Kubernetes Pod per task instance and terminates it on completion; ideal for heterogeneous dependencies, strict isolation, and bursty compute.

---

### Q12: How do Airflow Pools and `max_active_tasks` prevent overwhelming downstream databases?
**Answer**:
Create a named **Pool** (e.g., `postgres_oltp_pool` with `slots=4`) and assign `pool="postgres_oltp_pool"` to tasks hitting that database. Even if 50 DAGs trigger simultaneously, Airflow limits concurrent connections to 4, protecting OLTP systems from connection exhaustion.

---

### Q13: What are Custom XCom Backends, and why shouldn't you pass DataFrames through default XCom?
**Answer**:
Default XCom serializes payloads into the Airflow metadata database (Postgres/MySQL), which breaks or degrades DB performance above ~48 KB–1 MB. A **Custom XCom Backend** transparently offloads large objects to S3/GCS/ADLS and stores only the object URI reference in the metadata DB.

---

### Q14: What is the difference between `TriggerRule.ALL_SUCCESS`, `ALL_DONE`, `ONE_FAILED`, and `NONE_FAILED_MIN_ONE_SUCCESS`?
**Answer**:
- `ALL_SUCCESS` (default): Runs only if all upstream tasks succeeded.
- `ALL_DONE`: Runs once all upstream tasks finish regardless of success/failure (useful for cleanup/cluster teardown).
- `ONE_FAILED`: Triggers alert/DLQ handlers immediately when any upstream task fails.
- `NONE_FAILED_MIN_ONE_SUCCESS`: Essential after `BranchPythonOperator` so downstream join tasks run even though unchosen branches were `SKIPPED`.

---

### Q15: Explain Deferrable Operators and the Airflow Triggerer component.
**Answer**:
Traditional sensors or polling operators tie up an entire worker process/pod while waiting on a long external Spark/ADF/Databricks job. **Deferrable Operators** (`deferrable=True`) suspend execution and hand lightweight asyncio coroutines to the **Triggerer** process, freeing 100% of worker slots until the external event completes.

---

### Q16: How do you implement idempotency and safe backfilling in Airflow DAGs?
**Answer**:
Never use `datetime.now()` inside task business logic; parameterize queries and output paths using `{{ data_interval_start }}` and `{{ data_interval_end }}` (or `ds`), and overwrite target date partitions (`DELETE` + `INSERT` or `replaceWhere`) so re-running a past date never duplicates data.

---

### Q17: What is the purpose of Airflow Variables vs. Connections vs. Secrets Backends?
**Answer**:
- **Variables:** Key-value runtime configuration (e.g., table lists, thresholds). Avoid fetching them at top-level DAG parse time.
- **Connections:** Typed external system credentials/endpoints (`conn_id`).
- **Secrets Backends:** Pull Connections/Variables directly from AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault instead of storing them in Airflow's metadata DB.

---

### Q18: How do you test Airflow DAGs in CI/CD before deploying to production?
**Answer**:
1. **DagBag Integrity Test:** Load all DAGs with `DagBag()` and assert `len(dagbag.import_errors) == 0`, zero cycles, required tags/owners, and `catchup=False`.
2. **Unit Tests:** Test custom Operators, Hooks, and `@task` functions with mocked connections.
3. **Render & Dry-Run Tests:** Verify Jinja templates render cleanly for sample `logical_date` values.

---

### Q19: How do you monitor SLAs and prevent silent pipeline delays in Airflow?
**Answer**:
Configure `sla=timedelta(...)` (or Airflow 2.9+ SLA/timetable alerts + `sla_miss_callback`), `execution_timeout` on tasks (to kill hung jobs), and `on_failure_callback` posting structured Slack/PagerDuty alerts with DAG ID, task ID, `logical_date`, and log URL.

---

### Q20: What is `BranchPythonOperator` vs `@task.branch`, and what pitfall occurs with downstream tasks?
**Answer**:
Both evaluate a condition and return the `task_id`(s) to execute while marking other branches `SKIPPED`. The classic pitfall is forgetting `trigger_rule="none_failed_min_one_success"` on the downstream convergence task—with the default `all_success`, the downstream task gets skipped too!

---

### Q21: How do you handle `DagFileProcessor` parsing bottlenecks when you have 1,000+ DAGs?
**Answer**:
Eliminate top-level DB/API calls, move heavy Python imports inside task functions, increase `min_file_process_interval`, use DAG factory configs (JSON/YAML -> loop) carefully with serialized caching, and scale `parsing_processes`.

---

### Q22: When should Airflow orchestrate *external* compute vs. running Python transformations directly inside workers?
**Answer**:
Airflow is an **orchestrator, not a distributed data-processing engine**. Light API metadata calls or SQL triggers can run in workers, while GB/TB transformations should be delegated to Spark, Databricks, dbt, Snowflake, or EMR via Operators (`SparkSubmitOperator`, `DatabricksSubmitRunOperator`, `SnowflakeOperator`).

---

### Q23: How do you dynamically generate DAGs from YAML configuration files without breaking Task ID stability?
**Answer**:
Iterate over a deterministic YAML manifest in a generator script, assign stable `dag_id` and `task_id` slugs (never timestamps or random UUIDs), and validate generated DAGs via `DagBag` tests in CI.

---

### Q24: What happens if `max_active_runs=1` is set on a DAG during a multi-day catchup?
**Answer**:
Airflow executes queued `DagRun`s strictly one at a time sequentially (chronologically if `depends_on_past=True`), preventing concurrent runs from racing on shared tables or overrunning warehouse capacity.

---

### Q25: How do `depends_on_past=True` and `wait_for_downstream=True` control task execution order?
**Answer**:
- `depends_on_past=True`: Task instance for day $T$ will not run unless the same task succeeded (or was skipped) for day $T-1$.
- `wait_for_downstream=True`: Implies `depends_on_past=True` and additionally waits for immediate downstream tasks of day $T-1$ to succeed before starting day $T$.
