# Enterprise Data Fabric Platform

> **Project 22**: Production-ready Enterprise Data Fabric & Intelligent Metadata Platform

## Overview

The Enterprise Data Fabric platform is a comprehensive, production-grade solution for intelligent metadata management, data governance, and semantic data integration across distributed enterprise environments.

### What is Data Fabric?

Data Fabric is an architecture that connects and integrates data across distributed environments through intelligent metadata, semantic abstraction, and automated governance. It provides a unified view of all enterprise data assets, enabling data discovery, lineage tracking, policy enforcement, and self-service analytics.

### Key Features

- **Active Metadata Management**: Real-time metadata harvesting and event-driven updates
- **Knowledge Graph**: Neo4j-based relationship mapping for complex queries
- **Enterprise Catalog**: Advanced search, discovery, and data product identification
- **Semantic Layer**: Business glossary, taxonomy, and unified vocabulary
- **Policy Engine**: Automated governance with policy-as-code
- **Multi-Platform Integration**: Snowflake, Databricks, Kafka, Airflow, dbt, AWS Glue, Azure ADF, Unity Catalog
- **Intelligent Search**: Faceted search with auto-complete and recommendations
- **Lineage Tracking**: Cross-platform data lineage and impact analysis
- **Data Discovery**: Automated PII/PHI detection, sensitive data classification, orphaned asset detection
- **REST API**: Complete API layer for integration and automation
- **Monitoring**: Health checks, metrics, SLA tracking
- **CI/CD Ready**: Automated testing, deployment, and validation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Consumption Layer                         │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │   Analytics  │   BI Tools   │  ML/AI Apps  │   APIs   │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Platform Services                         │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │     Search   │  Discovery   │    Catalog   │ Lineage  │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Governance Layer                          │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │    Policies  │    RBAC      │  Audit Logs  │   SLA    │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Knowledge Layer                           │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │  Knowledge   │  Glossary    │   Semantic   │ Contracts│  │
│  │    Graph     │              │    Layer     │          │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Metadata Layer                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │   Technical  │   Business   │  Operational │ Versioning│  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Integration Layer                         │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │  Connectors  │  Harvesters  │   Events     │   APIs   │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Core Technologies
- **Language**: Python 3.13+
- **API Framework**: FastAPI
- **Metadata Storage**: PostgreSQL
- **Graph Database**: Neo4j 5.x
- **Cache**: Redis 7.x
- **Message Queue**: Apache Kafka
- **Orchestration**: Apache Airflow

### Data Platforms
- **Warehouses**: Snowflake, Databricks, Google BigQuery
- **Streaming**: Kafka, Spark Structured Streaming
- **Lakehouse**: Delta Lake, Databricks Unity Catalog
- ** orchestration**: Airflow, dbt, Azure Data Factory, AWS Glue

### Quality & Governance
- **Data Quality**: Great Expectations, Soda
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: Black, Ruff, MyPy
- **Monitoring**: Prometheus, health checks, SLA tracking

## Project Structure

```
projects/22_enterprise_data_fabric/
├── README.md                           # This file
├── architecture.md                      # System architecture
├── metadata-architecture.md             # Metadata layer design
├── governance.md                        # Governance framework
├── semantic-layer.md                    # Semantic layer guide
├── deployment-guide.md                  # Deployment instructions
├── interview-questions.md               # 45+ interview questions
├── requirements.txt                     # Python dependencies
├── platform/                            # Core platform services
│   ├── metadata/                        # Metadata management
│   │   ├── models.py                    # Asset, Column, Sensitivity models
│   │   ├── repository.py                # PostgreSQL repository
│   │   └── harvester.py                 # Metadata harvesting engine
│   ├── knowledge_graph/                 # Knowledge graph
│   │   ├── models.py                    # Graph node/edge models
│   │   ├── graph.py                     # Neo4j graph operations
│   │   └── traversal.py                 # Graph traversal algorithms
│   ├── glossary/                        # Business glossary
│   │   ├── models.py                    # Term, Category models
│   │   └── service.py                   # Glossary management
│   ├── semantic/                        # Semantic layer
│   │   ├── models.py                    # Business term mappings
│   │   └── query.py                     # Semantic query engine
│   ├── lineage/                         # Lineage tracking
│   │   ├── models.py                    # Lineage models
│   │   └── tracker.py                   # Lineage tracker
│   ├── catalog/                         # Data catalog
│   │   └── catalog.py                   # Catalog service
│   ├── search/                          # Intelligent search
│   │   └── search.py                    # Search service
│   ├── discovery/                       # Data discovery
│   │   └── discovery.py                 # Discovery service
│   ├── policies/                        # Policy engine
│   │   ├── models.py                    # Policy, Rule models
│   │   └── engine.py                    # Policy evaluation engine
│   ├── automation/                      # Automation
│   │   └── scheduler.py                 # Task scheduler
│   ├── monitoring/                      # Monitoring
│   │   ├── models.py                    # Metric, HealthCheck models
│   │   ├── metrics.py                   # Metrics collector
│   │   ├── health.py                    # Health checker
│   │   └── sla_tracker.py               # SLA tracker
│   └── connectors/                      # Base connector classes
│       └── base.py                      # BaseConnector
├── connectors/                          # Platform connectors
│   ├── airflow/connector.py             # Airflow metadata
│   ├── snowflake/connector.py           # Snowflake integration
│   ├── databricks/connector.py          # Databricks Unity
│   ├── kafka/connector.py               # Kafka streaming
│   ├── dbt/connector.py                 # dbt models
│   ├── aws/glue_connector.py            # AWS Glue
│   ├── azure/adf_connector.py           # Azure Data Factory
│   └── rest/connector.py                # Generic REST API
├── apis/                                # API layer
│   └── main.py                          # FastAPI application
├── tests/                               # Test suite
│   ├── test_catalog.py                  # Catalog tests
│   ├── test_policy_engine.py            # Policy tests
│   ├── test_discovery.py                # Discovery tests
│   └── test_search.py                   # Search tests
├── configs/                             # Configuration files
├── scripts/                             # Utility scripts
├── docs/                                # Documentation
├── diagrams/                            # Architecture diagrams
└── cicd/                                # CI/CD pipelines
```

## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose
- PostgreSQL 14+
- Neo4j 5.x
- Redis 7.x

### Installation

```bash
# Clone repository
git clone <repository-url>
cd production-data-engineering-projects/projects/22_enterprise_data_fabric

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python scripts/init_database.py

# Start services
docker-compose up -d

# Run API server
uvicorn apis.main:create_app --reload
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=platform --cov-report=html

# Run specific test
pytest tests/test_catalog.py -v
```

## Core Concepts

### Active Metadata

Active Metadata is the foundation of Data Fabric:
- **Real-time Updates**: Continuously synchronized from source systems
- **Event-Driven**: Changes trigger automated workflows
- **Connected**: Linked through knowledge graphs
- **Actionable**: Drives governance and optimization

### Knowledge Graph

Neo4j-based graph database storing:
- **Assets**: Tables, pipelines, reports, APIs
- **Relationships**: Lineage, ownership, dependencies
- **Properties**: Tags, classifications, scores

### Semantic Layer

Business abstraction providing:
- **Business Glossary**: Standardized definitions
- **Taxonomy**: Hierarchical categorization
- **Data Contracts**: Producer-consumer agreements
- **Metric Definitions**: Consistent calculations

### Policy Engine

Automated governance through:
- **Policy-as-Code**: Versioned rules in YAML/JSON
- **Real-time Validation**: Check on asset registration
- **Violation Tracking**: Audit trail and reporting
- **Automated Actions**: Alert, mask, encrypt, block

## Usage Examples

### Register an Asset

```python
from platform.metadata.models import Asset, AssetType
from platform.catalog.catalog import CatalogService

asset = Asset(
    name="customer_orders",
    description="Customer order transactions",
    asset_type=AssetType.TABLE,
    platform="snowflake",
    platform_id="analytics.public.orders",
    domain="sales",
    owner="data-team",
    tags=["customer", "transactional"],
)

catalog = CatalogService(repository)
registered = catalog.register_asset(asset)
print(f"Registered: {registered.urn}")
```

### Search Assets

```python
from platform.search.search import SearchService

search = SearchService(catalog)
results = search.search("customer orders")

for result in results:
    asset = result["asset"]
    print(f"{asset.name}: {result['score']}")
```

### Get Lineage

```python
from platform.lineage.tracker import LineageTracker

lineage = tracker.get_lineage("urn:li:dataset:(snowflake,analytics.public.orders)")
for node in lineage["nodes"]:
    print(node["name"])
for edge in lineage["edges"]:
    print(f"{edge['source']} -> {edge['target']}")
```

### Validate Policies

```python
from platform.policies.engine import PolicyEngine

engine = PolicyEngine()
violations = engine.evaluate_asset(asset.model_dump())

for v in violations:
    print(f"Violation: {v.policy_id} - {v.rule_condition}")
```

### Harvest Metadata

```python
from connectors.snowflake import SnowflakeConnector
from platform.metadata.harvester import MetadataHarvester

connector = SnowflakeConnector(config)
harvester = MetadataHarvester(catalog)
harvester.register_connector("snowflake", connector)

results = await harvester.harvest_all()
print(f"Harvested {results['snowflake']['assets_harvested']} assets")
```

## API Reference

### Asset Endpoints

```
POST   /api/v1/assets           Create asset
GET    /api/v1/assets           List assets
GET    /api/v1/assets/{urn}     Get asset
PUT    /api/v1/assets/{urn}     Update asset
DELETE /api/v1/assets/{urn}     Delete asset
```

### Search Endpoints

```
GET    /api/v1/search?q=query   Search assets
GET    /api/v1/search/suggestions?prefix=cust   Get suggestions
```

### Lineage Endpoints

```
GET    /api/v1/assets/{urn}/lineage      Get lineage graph
GET    /api/v1/assets/{urn}/dependencies  Get dependencies
```

### Governance Endpoints

```
POST   /api/v1/policies/validate        Validate asset policies
GET    /api/v1/policies/report          Compliance report
```

### Discovery Endpoints

```
GET    /api/v1/discovery/report          Discovery report
GET    /api/v1/discovery/sensitive       Find sensitive data
```

## Business Scenarios

### 1. Enterprise Customer 360
Unify customer data across CRM, support, and transactional systems with automatic PII detection and lineage tracking.

### 2. Global Payment Platform
Ensure PCI compliance with sensitive data classification, policy enforcement, and complete audit trails.

### 3. Healthcare Information Exchange
Maintain HIPAA compliance with PHI detection, access controls, and comprehensive data lineage.

### 4. Insurance Data Platform
Connect policy, claims, and underwriting data with business glossary and semantic search.

### 5. Retail Commerce Platform
Integrate e-commerce, POS, and inventory systems with real-time metadata synchronization.

### 6. Supply Chain Network
Track materials, logistics, and suppliers with cross-platform lineage and impact analysis.

### 7. Marketing Intelligence
Connect campaign, customer, and analytics data with data product certification.

### 8. Executive Reporting
Provide trusted, certified data products with quality metrics and SLA tracking.

## Monitoring

### Health Checks

```bash
GET /health              # Overall health
GET /health/detailed     # Component details
```

### Metrics

```bash
GET /metrics             # Prometheus metrics
GET /api/v1/stats        # Catalog statistics
```

### Dashboards

- **Asset Growth**: Track catalog expansion
- **Harvest Status**: Monitor connector health
- **Search Performance**: Query latency and usage
- **Policy Compliance**: Violation trends
- **Quality Metrics**: Data quality scores

## Deployment

### Docker Compose

```bash
docker-compose up -d
```

### Kubernetes

```bash
kubectl apply -f infrastructure/kubernetes/
```

### Terraform (Cloud)

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

See [deployment-guide.md](deployment-guide.md) for detailed instructions.

## Testing

The project includes comprehensive tests:

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Performance tests
pytest tests/performance/ -v

# All tests with coverage
pytest tests/ -v --cov=platform --cov-report=html
```

## Documentation

- [Architecture](architecture.md) - System design
- [Metadata Architecture](metadata-architecture.md) - Metadata layer
- [Governance](governance.md) - Policy framework
- [Semantic Layer](semantic-layer.md) - Business glossary
- [Deployment Guide](deployment-guide.md) - Production deployment
- [Interview Questions](interview-questions.md) - 45+ questions

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](../../LICENSE) for details.

## Support

- **Documentation**: https://data-fabric.example.com/docs
- **Issues**: https://github.com/org/data-fabric/issues
- **Email**: support@example.com

---

**Status**: ✅ Production-Ready  
**Version**: 1.0.0  
**Last Updated**: 2026-07-31