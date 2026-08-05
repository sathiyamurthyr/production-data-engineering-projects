#!/usr/bin/env python3
"""Generate all design pattern scaffolds from a definition list.

Usage:
    python scripts/generate_all_patterns.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PATTERNS: dict[str, list[tuple[str, str]]] = {
    "architecture-patterns": [
        ("layered-architecture", "Layered Architecture"),
        ("medallion-architecture", "Medallion Architecture"),
        ("lambda-architecture", "Lambda Architecture"),
        ("kappa-architecture", "Kappa Architecture"),
        ("data-mesh", "Data Mesh"),
        ("data-fabric", "Data Fabric"),
        ("lakehouse", "Lakehouse"),
        ("warehouse", "Enterprise Data Warehouse"),
        ("hub-and-spoke", "Hub-and-Spoke"),
        ("microservices-for-data", "Microservices for Data"),
        ("event-driven", "Event Driven"),
        ("cqrs", "CQRS Concepts"),
        ("domain-driven-design", "Domain Driven Design"),
        ("hexagonal-architecture", "Hexagonal Architecture"),
        ("clean-architecture", "Clean Architecture"),
    ],
    "ingestion-patterns": [
        ("batch-load", "Batch Load"),
        ("incremental-load", "Incremental Load"),
        ("full-refresh", "Full Refresh"),
        ("cdc", "Change Data Capture"),
        ("snapshot", "Snapshot"),
        ("micro-batch", "Micro Batch"),
        ("streaming-ingestion", "Streaming Ingestion"),
        ("webhook-ingestion", "Webhook Ingestion"),
        ("api-pagination", "API Pagination"),
        ("file-drop", "File Drop"),
    ],
    "etl-patterns": [
        ("extract-pattern", "Extract Pattern"),
        ("transformation-pattern", "Transformation Pattern"),
        ("load-pattern", "Load Pattern"),
        ("validation-pattern", "Validation Pattern"),
        ("deduplication", "Deduplication"),
        ("merge", "Merge"),
        ("scd-type-1", "SCD Type 1"),
        ("scd-type-2", "SCD Type 2"),
        ("scd-type-3", "SCD Type 3"),
        ("surrogate-keys", "Surrogate Keys"),
        ("business-keys", "Business Keys"),
        ("audit-columns", "Audit Columns"),
        ("error-handling", "Error Handling"),
        ("retry-logic", "Retry Logic"),
        ("checkpointing", "Checkpointing"),
    ],
    "elt-patterns": [
        ("elt-pipeline", "ELT Pipeline"),
        ("schema-evolution", "Schema Evolution"),
        ("transformation-in-warehouse", "Data Transformation in Warehouse"),
        ("incremental-elt", "Incremental ELT"),
        ("temp-tables", "ELT with Temp Tables"),
        ("stored-procedures", "ELT with Stored Procedures"),
        ("views", "ELT with Views"),
        ("materialized-views", "ELT with Materialized Views"),
        ("ctas", "ELT with CTAS"),
        ("ddl", "ELT with DDL"),
    ],
    "cdc-patterns": [
        ("log-based-cdc", "Log-based CDC"),
        ("trigger-based-cdc", "Trigger-based CDC"),
        ("timestamp-based-cdc", "Timestamp-based CDC"),
        ("polling-cdc", "Polling CDC"),
        ("schema-drift-cdc", "Schema Drift CDC"),
        ("multi-table-cdc", "Multi-table CDC"),
        ("cdc-checkpointing", "CDC with Checkpointing"),
        ("cdc-ordering", "CDC with Ordering"),
        ("cdc-dlq", "CDC with Dead Letter Queue"),
        ("cdc-schema-registry", "CDC with Schema Registry"),
    ],
    "streaming-patterns": [
        ("event-time", "Event Time"),
        ("processing-time", "Processing Time"),
        ("watermark", "Watermark"),
        ("windowing", "Windowing"),
        ("exactly-once", "Exactly Once Concepts"),
        ("at-least-once", "At Least Once"),
        ("dead-letter-queue", "Dead Letter Queue"),
        ("replay", "Replay"),
        ("backpressure", "Backpressure"),
        ("state-store", "State Store"),
        ("streaming-join", "Streaming Join"),
        ("streaming-aggregation", "Streaming Aggregation"),
        ("stream-table-join", "Stream-Table Join"),
        ("late-data-handling", "Late Data Handling"),
        ("window-trigger", "Window Trigger"),
    ],
    "spark-patterns": [
        ("broadcast-join", "Broadcast Join"),
        ("partitioning", "Partitioning"),
        ("bucketing", "Bucketing Concepts"),
        ("caching", "Caching"),
        ("adaptive-query-execution", "Adaptive Query Execution"),
        ("skew-handling", "Skew Handling"),
        ("small-files", "Small Files"),
        ("shuffle-optimization", "Shuffle Optimization"),
        ("spark-checkpointing", "Checkpointing"),
        ("columnar", "Columnar Processing"),
    ],
    "delta-patterns": [
        ("delta-merge", "MERGE"),
        ("delta-optimize", "OPTIMIZE"),
        ("delta-vacuum", "VACUUM"),
        ("time-travel", "Time Travel"),
        ("delta-cdc", "CDC with Delta"),
        ("schema-evolution-delta", "Schema Evolution"),
        ("liquid-clustering", "Liquid Clustering Concepts"),
        ("zorder", "ZORDER"),
    ],
    "databricks-patterns": [
        ("autoloader", "Auto Loader"),
        ("databricks-sql", "Databricks SQL"),
        ("unity-catalog", "Unity Catalog"),
        ("databricks-jobs", "Databricks Jobs"),
        ("feature-store", "Feature Store"),
        ("model-serving", "Model Serving"),
        ("workflows", "Workflows"),
    ],
    "airflow-patterns": [
        ("task-groups", "Task Groups"),
        ("dynamic-dags", "Dynamic DAGs"),
        ("sensors", "Sensors"),
        ("datasets", "Datasets"),
        ("retries", "Retries"),
        ("backfills", "Backfills"),
        ("slas", "SLAs"),
        ("branching", "Branching"),
        ("pools", "Pools"),
        ("priority-weights", "Priority Weights"),
    ],
    "kafka-patterns": [
        ("topic-design", "Topic Design"),
        ("partition-strategy", "Partition Strategy"),
        ("consumer-groups", "Consumer Groups"),
        ("dlq", "Dead Letter Queue"),
        ("schema-registry", "Schema Registry Concepts"),
        ("idempotent-producer", "Idempotent Producer Concepts"),
        ("transactions", "Transactions Concepts"),
        ("compaction", "Log Compaction"),
    ],
    "snowflake-patterns": [
        ("compute-management", "Compute Management"),
        ("clustering-keys", "Clustering Keys"),
        ("materialized-views", "Materialized Views"),
        ("streams", "Streams"),
        ("zero-copy-clone", "Zero Copy Cloning"),
        ("data-sharing", "Data Sharing"),
    ],
    "dbt-patterns": [
        ("staging-models", "Staging Models"),
        ("mart-models", "Mart Models"),
        ("snapshots", "Snapshots"),
        ("incremental-models", "Incremental Models"),
        ("tests", "Tests"),
        ("macros", "Macros"),
    ],
    "lakehouse-patterns": [
        ("bronze-layer", "Bronze Layer"),
        ("silver-layer", "Silver Layer"),
        ("gold-layer", "Gold Layer"),
        ("lakehouse-ingestion", "Lakehouse Ingestion"),
    ],
    "metadata-patterns": [
        ("metadata-catalog", "Metadata Catalog"),
        ("data-lineage", "Data Lineage"),
        ("schema-registry-m", "Schema Registry"),
        ("data-discovery", "Data Discovery"),
        ("business-glossary", "Business Glossary"),
    ],
    "governance-patterns": [
        ("rbac-gov", "RBAC"),
        ("least-privilege-gov", "Least Privilege"),
        ("audit-logging", "Audit Logging"),
        ("data-retention", "Data Retention"),
        ("compliance-reporting", "Compliance Reporting"),
        ("data-access-control", "Data Access Control"),
        ("policy-enforcement", "Policy Enforcement"),
    ],
    "quality-patterns": [
        ("data-validation", "Data Validation"),
        ("data-quality-monitoring", "Data Quality Monitoring"),
        ("anomaly-detection", "Anomaly Detection"),
        ("data-reconciliation", "Data Reconciliation"),
        ("referential-integrity", "Referential Integrity"),
    ],
    "observability-patterns": [
        ("metrics", "Metrics"),
        ("logs", "Logs"),
        ("tracing", "Tracing Concepts"),
        ("slis", "SLIs"),
        ("slos", "SLOs"),
        ("alerting", "Alerting"),
        ("runbooks", "Runbooks"),
    ],
    "security-patterns": [
        ("rbac-sec", "RBAC"),
        ("secrets-management", "Secrets Management"),
        ("encryption", "Encryption"),
        ("data-masking", "Data Masking"),
        ("pii-protection", "PII Protection"),
        ("zero-trust", "Zero Trust Concepts"),
    ],
    "platform-patterns": [
        ("internal-developer-platform", "Internal Developer Platform"),
        ("golden-path", "Golden Path"),
        ("infrastructure-as-code", "Infrastructure as Code"),
        ("gitops", "GitOps Concepts"),
        ("service-catalog", "Service Catalog"),
        ("self-service-provisioning", "Self-Service Provisioning"),
        ("terraform-modules", "Terraform Modules"),
    ],
    "ai-patterns": [
        ("rag", "RAG"),
        ("prompt-engineering", "Prompt Engineering"),
        ("chunking", "Chunking"),
        ("embeddings", "Embeddings"),
        ("hybrid-search", "Hybrid Search"),
        ("vector-search", "Vector Search"),
    ],
    "mlops-patterns": [
        ("model-registry", "Model Registry"),
        ("experiment-tracking", "Experiment Tracking"),
        ("feature-store", "Feature Store"),
        ("model-deployment", "Model Deployment"),
        ("model-monitoring", "Model Monitoring"),
    ],
    "rag-patterns": [
        ("document-ingestion", "Document Ingestion"),
        ("embedding-generation", "Embedding Generation"),
        ("vector-storage", "Vector Storage"),
        ("similarity-search", "Similarity Search"),
    ],
    "agent-patterns": [
        ("tool-registry", "Tool Registry"),
        ("conversation-memory", "Conversation Memory"),
        ("agent-orchestration", "Agent Orchestration"),
    ],
    "multicloud-patterns": [
        ("multi-region", "Multi-Region Deployment"),
        ("hybrid-cloud", "Hybrid Cloud"),
        ("cloud-migration", "Cloud Migration"),
        ("disaster-recovery", "Disaster Recovery"),
    ],
    "sre-patterns": [
        ("slo-definition", "SLO Definition"),
        ("error-budget", "Error Budget"),
        ("incident-response-sre", "Incident Response"),
        ("capacity-planning", "Capacity Planning"),
        ("chaos-engineering-sre", "Chaos Engineering"),
    ],
    "finops-patterns": [
        ("cost-allocation", "Cost Allocation"),
        ("budget-monitoring", "Budget Monitoring"),
        ("cost-anomaly-detection", "Cost Anomaly Detection"),
        ("resource-right-sizing", "Resource Right Sizing"),
    ],
    "devops-patterns": [
        ("ci-cd", "CI/CD Pipeline"),
        ("infrastructure-testing", "Infrastructure Testing"),
        ("feature-flag", "Feature Flag"),
        ("containerization", "Containerization"),
    ],
}


def make_class_name(pattern_name: str) -> str:
    """Convert pattern name to CamelCase class name."""
    return "".join(
        w.capitalize() for w in pattern_name.replace("-", " ").split()
    )


def make_safe_name(pattern_name: str) -> str:
    """Convert pattern name to snake_case for file naming."""
    return pattern_name.replace("-", "_")


def create_pattern(category: str, pattern_name: str, display_name: str) -> bool:
    """Create a complete pattern scaffold.

    Args:
        category: The category directory name.
        pattern_name: The pattern directory name (kebab-case).
        display_name: The human-readable display name.

    Returns:
        True if successful.
    """
    safe_name = make_safe_name(pattern_name)
    class_name = make_class_name(pattern_name)
    pd = REPO / category / pattern_name
    src_dir = pd / "src"
    tests_dir = pd / "tests"
    bench_dir = pd / "benchmarks"
    ds_dir = pd / "datasets"
    mm_dir = pd / "mermaid"
    infra_dir = pd / "infrastructure"

    for d in [src_dir, tests_dir, bench_dir, ds_dir, mm_dir, infra_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # __init__.py for src
    (src_dir / "__init__.py").write_text(
        f'"""{display_name} pattern."""\n'
    )
    (tests_dir / "__init__.py").write_text("")

    # main source file
    src_code = f'''"""{display_name} pattern - Production implementation."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class {class_name}Config(BaseModel):
    """Configuration for the {display_name} pattern."""

    pattern_name: str = Field(default="{pattern_name}")
    # Add pattern-specific configuration fields here


class {class_name}:
    """{display_name} pattern implementation.

    Args:
        config: Pattern configuration.

    Example:
        >>> config = {class_name}Config()
        >>> pattern = {class_name}(config)
        >>> result = pattern.execute(data)
    """

    def __init__(self, config: {class_name}Config | None = None) -> None:
        self.config = config or {class_name}Config()
        self.logger = logging.getLogger(f"{{__name__}}.{{self.__class__.__name__}}")

    def execute(self, data: Any) -> Any:
        """Execute the {display_name} pattern.

        Args:
            data: Input data to process.

        Returns:
            Processed data according to the pattern.
        """
        self.logger.info(
            "Executing {display_name} pattern",
            pattern=self.config.pattern_name,
        )
        return data
'''
    (src_dir / f"{safe_name}.py").write_text(src_code)

    # tests
    test_code = f'''"""Unit tests for the {display_name} pattern."""

import pytest

from src.{safe_name} import {class_name}, {class_name}Config


class Test{class_name}Config:
    """Tests for {class_name}Config."""

    def test_default_config(self) -> None:
        config = {class_name}Config()
        assert config.pattern_name == "{pattern_name}"


class Test{class_name}:
    """Tests for {class_name}."""

    def test_init_default_config(self) -> None:
        pattern = {class_name}()
        assert pattern.config.pattern_name == "{pattern_name}"

    def test_init_custom_config(self) -> None:
        config = {class_name}Config()
        pattern = {class_name}(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = {class_name}()
        result = pattern.execute("test_data")
        assert result == "test_data"
'''
    (tests_dir / f"test_{safe_name}.py").write_text(test_code)

    # benchmark
    bench_code = f'''"""Benchmarks for the {display_name} pattern."""

from __future__ import annotations

import time

from src.{safe_name} import {class_name}


def benchmark_execute() -> None:
    """Benchmark the execute method."""
    pattern = {class_name}()
    data = "sample_data"

    start = time.perf_counter()
    for _ in range(1000):
        pattern.execute(data)
    elapsed = time.perf_counter() - start

    print(f"1000 executions: {{elapsed:.4f}}s ({{elapsed/1000*1000:.2f}}ms per call)")


if __name__ == "__main__":
    benchmark_execute()
'''
    (bench_dir / f"benchmark_{safe_name}.py").write_text(bench_code)

    # mermaid diagram
    mmd_content = (
        f"%% {display_name} Architecture Diagram\ngraph LR\n"
        "    A[Input] --> B[Processing]\n"
        "    B --> C[Output]\n"
    )
    (mm_dir / "architecture.mmd").write_text(mmd_content)

    # README.md
    readme = f'''# {display_name} Pattern

## Business Problem

[Describe the specific business problem this pattern addresses]

## Context

[Describe the context, when to use this pattern, and the forces at play]

## Architecture

```mermaid
{mmd_content}
```

### Components

[List and describe the key components]

## Decision Criteria

[When to use this pattern vs alternatives]

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Factor] | [Choice] | [Why this choice] |

## Advantages

- [Advantage 1]
- [Advantage 2]

## Limitations

- [Limitation 1]
- [Limitation 2]

## Performance Considerations

[Performance implications and optimization tips]

## Security Considerations

[Security implications and best practices]

## Cost Considerations

[Cost implications and optimization strategies]

## Operational Guidance

[Operational best practices, monitoring, alerting]

## Anti-patterns

[List common misuse scenarios and how to avoid them]

## Real Enterprise Use Cases

[List real enterprise use cases]

## References

[List references and further reading]
'''
    (pd / "README.md").write_text(readme)

    # Other doc files
    docs = {
        "architecture.md": f"# {display_name} - Architecture\n\n[Architecture description]\n",
        "implementation.md": f"# {display_name} - Implementation\n\n[Implementation guide]\n",
        "decision-matrix.md": f"# {display_name} - Decision Matrix\n\n[Decision matrix]\n",
        "anti-patterns.md": f"# {display_name} - Anti-patterns\n\n[Anti-patterns]\n",
        "performance.md": f"# {display_name} - Performance\n\n[Performance analysis]\n",
        "security.md": f"# {display_name} - Security\n\n[Security considerations]\n",
        "operations.md": f"# {display_name} - Operations\n\n[Operational guidance]\n",
        "cost-analysis.md": f"# {display_name} - Cost Analysis\n\n[Cost analysis]\n",
        "deployment-guide.md": f"# {display_name} - Deployment Guide\n\n[Deployment guide]\n",
        "troubleshooting.md": f"# {display_name} - Troubleshooting\n\n[Troubleshooting]\n",
        "interview-questions.md": f"# {display_name} - Interview Questions\n\n[Interview questions]\n",
        "requirements.txt": f"# {display_name} dependencies\n",
    }
    for doc_name, content in docs.items():
        (pd / doc_name).write_text(content)

    return True


def main() -> int:
    """Generate all patterns."""
    total = 0
    for category, pattern_list in PATTERNS.items():
        for name, display in pattern_list:
            try:
                create_pattern(category, name, display)
                total += 1
            except Exception as e:
                print(f"FAIL: {category}/{name}: {e}", file=sys.stderr)
        print(f"[{category}] ({len(pattern_list)} patterns) - done")

    print(f"\n{'='*60}")
    print(f"Total patterns generated: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
