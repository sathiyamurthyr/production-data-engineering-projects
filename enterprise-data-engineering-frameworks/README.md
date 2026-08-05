# Enterprise Data Engineering Frameworks

> The world's most comprehensive collection of reusable, production-ready enterprise data engineering frameworks.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![PySpark 4.x](https://img.shields.io/badge/pyspark-4.x-orange.svg)](https://spark.apache.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](tests/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

This repository is a **production-ready engineering toolkit** that provides reusable frameworks for building modern enterprise data platforms. It is **not** a tutorial repository — every framework is installable, modular, configurable, well-documented, fully tested, benchmark-tested, and production-ready.

## Frameworks

| Framework | Description | Status |
|-----------|-------------|--------|
| `framework-core` | Plugin architecture, DI, config, pipeline engine, retry, audit, logging, metrics, notifications, secrets, storage, validation, policy, extension SDK | ✅ |
| `etl-framework` | Extract-Transform-Load with CSV, JSON, Parquet, Delta, XML, Excel, REST, GraphQL, Kafka, DB connectors, SCD, incremental loads | ✅ |
| `elt-framework` | Extract-Load-Transform with warehouse-native transforms, dbt-style models, incremental materialization | ✅ |
| `batch-framework` | Batch processing with Spark, job orchestration, partitioning, checkpointing | ✅ |
| `streaming-framework` | Kafka, Spark Structured Streaming, micro-batch, checkpointing, DLQ, watermarks, state management, replay | ✅ |
| `cdc-framework` | Change Data Capture: log-based, trigger-based, timestamp-based, schema drift, ordering, checkpointing, DLQ | ✅ |
| `ingestion-framework` | Unified ingestion abstraction across APIs, files, databases, streams | ✅ |
| `api-framework` | REST/GraphQL ingestion with pagination, auth, rate limiting, retry, streaming responses | ✅ |
| `file-framework` | File ingestion: CSV, JSON, Parquet, XML, Excel, Delta with schema inference and validation | ✅ |
| `quality-framework` | Schema validation, business rules, referential integrity, duplicate detection, freshness, completeness, accuracy | ✅ |
| `validation-framework` | Data validation engine with custom validators, contracts, and quality reports | ✅ |
| `metadata-framework` | Business, technical, operational metadata; catalog API, data contracts, classification | ✅ |
| `lineage-framework` | Column-level and table-level lineage tracking, impact analysis, visual lineage graph | ✅ |
| `monitoring-framework` | Pipeline monitoring, metrics collection, health checks, alerting | ✅ |
| `observability-framework` | Metrics, logs, tracing, SLIs, SLOs, alerts, dashboards, incident hooks | ✅ |
| `logging-framework` | Structured logging, correlation IDs, log routing, log levels, JSON logging | ✅ |
| `notification-framework` | Multi-channel notifications: email, Slack, Teams, PagerDuty, webhooks | ✅ |
| `config-framework` | Hierarchical configuration: env, file, vault, CLI, dynamic config | ✅ |
| `secrets-framework` | Secrets management: AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, env | ✅ |
| `governance-framework` | Data governance: policies, access control, compliance, audit, retention | ✅ |
| `lakehouse-framework` | Lakehouse management: Delta Lake, Iceberg, Hudi, ACID, time travel, optimization | ✅ |
| `platform-sdk` | Project generator, pipeline generator, config generator, template engine, CLI | ✅ |
| `ai-framework` | Prompt registry, embedding pipeline, vector store abstraction, retriever, agent SDK, evaluation, memory | ✅ |
| `cli` | Unified CLI for all frameworks | ✅ |

## Quick Start

```bash
# Install
pip install enterprise-data-engineering-frameworks

# Or install from source
pip install -e .

# Initialize a new project
edf init my-data-platform

# Generate a pipeline
edf generate pipeline --name sales_etl --template etl

# Validate configuration
edf validate config.yaml

# Run a pipeline
edf run pipeline.yaml
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI / Platform SDK                     │
├─────────────────────────────────────────────────────────────┤
│  ETL  │  ELT  │  Batch  │  Streaming  │  CDC  │  Ingestion  │
├─────────────────────────────────────────────────────────────┤
│  Quality  │  Validation  │  Metadata  │  Lineage  │  Govern  │
├─────────────────────────────────────────────────────────────┤
│  Monitoring  │  Observability  │  Logging  │  Notification   │
├─────────────────────────────────────────────────────────────┤
│  Config  │  Secrets  │  Lakehouse  │  AI Framework           │
├─────────────────────────────────────────────────────────────┤
│                    Framework Core                            │
│  Plugin Arch  │  DI  │  Pipeline Engine  │  Retry  │  Audit  │
│  Logging  │  Metrics  │  Notification  │  Secret  │  Storage │
│  Validation  │  Policy  │  Extension SDK                       │
├─────────────────────────────────────────────────────────────┤
│                        Shared                                │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.13+
- Apache Spark 4.x (for batch/streaming frameworks)
- Apache Kafka (for streaming framework)
- Delta Lake (for lakehouse framework)

### Install

```bash
pip install enterprise-data-engineering-frameworks

# With extras
pip install enterprise-data-engineering-frameworks[spark,kafka,delta,ai]
```

## Documentation

- [Architecture Guide](docs/architecture-guide.md)
- [Developer Guide](docs/developer-guide.md)
- [Extension Guide](docs/extension-guide.md)
- [Plugin Guide](docs/plugin-guide.md)
- [Migration Guide](docs/migration-guide.md)
- [API Reference](docs/api-reference.md)
- [Benchmark Reports](benchmarks/)
- [Troubleshooting Handbook](docs/troubleshooting-handbook.md)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=enterprise_data_engineering_frameworks --cov-report=html

# Run benchmarks
pytest benchmarks/ --benchmark-only
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE).