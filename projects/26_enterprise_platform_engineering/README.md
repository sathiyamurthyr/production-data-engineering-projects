# Enterprise Platform Engineering & Internal Developer Platform (IDP)

**Project 26** | Production-Ready Enterprise Platform Engineering

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![Terraform](https://img.shields.io/badge/terraform-%3E%3D1.5%2C-purple)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.28%2B-orange)](https://kubernetes.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

This project implements a world-class **Enterprise Platform Engineering** and **Internal Developer Platform (IDP)** for data and AI teams. It teaches platform engineering exactly as implemented by large enterprise organizations, focusing on self-service infrastructure, pipelines, data products, and AI services.

### What You'll Build

- **Self-Service Data Platform** - Data lakes, warehouses, pipelines
- **Self-Service AI Platform** - ML projects, AI agents, feature stores
- **Infrastructure Automation** - Environment provisioning, workspace management
- **Developer Portal** - Golden paths, templates, service catalog
- **Platform APIs & SDK** - Programmatic access to platform services
- **Governance & Security** - RBAC, policy as code, compliance
- **Observability** - Platform metrics, usage analytics, monitoring

### Who This Is For

- **Platform Engineers** building internal platforms
- **Data Engineers** seeking self-service capabilities
- **ML/AI Engineers** needing scalable infrastructure
- **Staff/Principal Engineers** designing enterprise architectures
- **Enterprise Architects** overseeing platform strategy

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer Portal                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Service     │  │  Golden      │  │  Developer   │      │
│  │   Catalog     │  │  Paths       │  │  Dashboard   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Platform APIs                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Provisioning │  │   Template   │  │  Governance  │      │
│  │     API      │  │     API      │  │     API      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Data        │      │     AI       │      │   Infra      │
│  Platform    │      │   Platform   │      │  Services    │
│              │      │              │      │              │
│ • Data Lake  │      │ • ML Projects│      │ • K8s        │
│ • Warehouse  │      │ • AI Agents  │      │ • Terraform  │
│ • Streaming  │      │ • Features   │      │ • Cloud      │
│ • Quality    │      │ • Models     │      │ • Secrets    │
└──────────────┘      └──────────────┘      └──────────────┘
```

## Key Features

### 🎯 Platform Engineering Principles
- Golden Paths for standardized deployments
- Self-service infrastructure provisioning
- Developer experience optimization
- Platform as a product mindset

### 🚀 Self-Service Capabilities
- **Data Platform**: Data lakes, Kafka topics, Airflow DAGs, Databricks workspaces, Snowflake warehouses
- **AI Platform**: ML projects, feature stores, model deployments, AI agents
- **Infrastructure**: Kubernetes namespaces, cloud resources, environments

### 🔒 Enterprise Governance
- Role-based access control (RBAC)
- Policy as code (OPA, Sentinel)
- Audit logging and compliance
- Cost allocation and chargeback

### 📊 Observability & Analytics
- Platform metrics and health monitoring
- Developer productivity analytics
- Resource utilization tracking
- Provisioning success rates

### 🔄 CI/CD & Automation
- GitHub Actions integration
- GitOps workflows (ArgoCD, Flux)
- Infrastructure as Code (Terraform, Pulumi)
- Automated testing and validation

## Quick Start

### Prerequisites

```bash
# Required
- Python 3.13+
- Terraform >= 1.5
- Kubernetes 1.28+ (minikube, kind, or cloud)
- Docker
- Git
- Azure CLI / AWS CLI (for cloud deployments)
```

### Installation

```bash
# Clone the repository
git clone https://github.com/sathiyamurthyr/production-data-engineering-projects.git
cd production-data-engineering-projects/projects/26_enterprise_platform_engineering

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

### Launch Developer Portal

```bash
# Start the platform portal locally
python -m platform.portal.app

# Access at http://localhost:8080
# Default credentials: admin@platform.local / admin123
```

### Deploy to Kubernetes

```bash
# Deploy platform services
terraform init && terraform apply

# Deploy Kubernetes manifests
kubectl apply -f kubernetes/

# Verify deployment
kubectl get pods -n platform-system
```

## Project Structure

```
projects/26_enterprise_platform_engineering/
├── README.md                    # This file
├── architecture.md              # Platform architecture documentation
├── idp-guide.md                 # Internal Developer Platform guide
├── developer-experience.md      # Developer experience best practices
├── governance.md                # Governance policies and procedures
├── deployment-guide.md          # Production deployment guide
├── troubleshooting.md           # Troubleshooting handbook
├── interview-questions.md       # 300+ interview questions
│
├── platform/                    # Core platform services
│   ├── portal/                  # Developer portal UI/API
│   ├── catalog/                 # Service catalog
│   ├── templates/               # Golden path templates
│   ├── scaffolding/             # Code scaffolding tools
│   ├── provisioning/            # Infrastructure provisioning
│   ├── automation/              # Workflow automation
│   ├── workflows/               # Approval workflows
│   ├── sdk/                     # Platform SDK (Python, CLI)
│   ├── apis/                    # REST/GraphQL APIs
│   └── governance/              # Policy engine, RBAC
│
├── services/                    # Platform services
│   ├── data-platform/           # Data lake, warehouse, streaming
│   ├── ai-platform/             # ML, feature store, models
│   ├── streaming/               # Kafka, streaming infrastructure
│   ├── analytics/               # Analytics services
│   ├── infrastructure/          # K8s, cloud, secrets
│   └── observability/           # Metrics, logging, tracing
│
├── terraform/                   # Infrastructure as Code
│   ├── modules/                 # Reusable Terraform modules
│   ├── environments/            # dev/staging/prod
│   └── backend/                 # State management
│
├── kubernetes/                  # Kubernetes manifests
│   ├── base/                    # Base deployments
│   ├── overlays/                # Environment-specific configs
│   └── helm/                    # Helm charts
│
├── configs/                     # Configuration files
│   ├── policies/                # OPA, Sentinel policies
│   ├── workflows/               # GitHub Actions, ArgoCD
│   └── templates/               # Template configurations
│
├── scripts/                     # Automation scripts
│   ├── setup/                   # Environment setup
│   ├── deployment/              # Deployment scripts
│   └── maintenance/             # Maintenance scripts
│
├── datasets/                    # Sample datasets
│   ├── platform/                # Platform demo data
│   └── exercises/               # Exercise datasets
│
├── dashboards/                  # Monitoring dashboards
│   ├── grafana/                 # Grafana dashboards
│   └── metrics/                 # Metric definitions
│
├── tests/                       # Comprehensive test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   └── performance/             # Performance benchmarks
│
├── benchmarks/                  # Performance benchmarks
│   ├── provisioning/            # Provisioning performance
│   ├── api/                     # API performance
│   └── template/                # Template rendering performance
│
├── docs/                        # Additional documentation
│   ├── api/                     # API reference
│   ├── guides/                  # How-to guides
│   └── examples/                # Usage examples
│
├── diagrams/                    # Mermaid diagrams
│   ├── architecture/            # Architecture diagrams
│   ├── workflows/               # Workflow diagrams
│   └── integration/             # Integration diagrams
│
├── images/                      # Documentation images
│
├── cicd/                        # CI/CD configurations
│   ├── github/                  # GitHub Actions
│   ├── templates/               # Reusable workflows
│   └── scripts/                 # CI scripts
│
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Python project config
├── .pre-commit-config.yaml     # Pre-commit hooks
└── Makefile                    # Build automation
```

## Module Guide

### Core Platform (Modules 01-10)
1. **Platform Engineering Principles** - Foundations of platform engineering
2. **Internal Developer Platform** - IDP concepts and design
3. **Platform Architecture** - Multi-layer architecture design
4. **Platform Portal** - Developer portal implementation
5. **Service Catalog** - Catalog design and management
6. **Platform APIs** - REST/GraphQL API design
7. **Developer Portal** - UX/UI for developers
8. **Golden Paths** - Standardized deployment patterns
9. **Project Templates** - Template system design
10. **Repository Templates** - Git repository templates

### Templates & Scaffolding (Modules 11-14)
11. **Pipeline Templates** - CI/CD pipeline templates
12. **Infrastructure Templates** - IaC templates
13. **Data Product Templates** - Data product patterns
14. **AI Project Templates** - ML/AI project templates

### Provisioning (Modules 15-19)
15. **Self-Service Provisioning** - Provisioning workflows
16. **Environment Provisioning** - Dev/staging/prod environments
17. **Workspace Provisioning** - Developer workspaces
18. **Infrastructure Provisioning** - Cloud/K8s resources
19. **Identity Integration** - SSO, RBAC, IAM

### SDK & Automation (Modules 20-24)
20. **Platform SDK** - Python SDK for platform interaction
21. **CLI Concepts** - Command-line interface design
22. **Platform Automation** - Automation frameworks
23. **Workflow Engine** - Workflow orchestration
24. **Approval Workflows** - Human-in-the-loop approvals

### Governance (Modules 25-28)
25. **Governance Policies** - Policy framework
26. **Cost Allocation** - Cost tracking and allocation
27. **Chargeback Concepts** - Chargeback models
28. **Platform Monitoring** - Monitoring infrastructure

### Analytics (Modules 29-31)
29. **Usage Analytics** - Platform usage tracking
30. **Developer Analytics** - Developer productivity metrics
31. **Resource Lifecycle** - Resource management

### Platform Services (Modules 32-36)
32. **Service Ownership** - Ownership models
33. **Dependency Mapping** - Service dependencies
34. **Platform Security** - Security architecture
35. **Secrets Management** - Vault, sealed secrets
36. **Policy as Code** - OPA, Sentinel, Kyverno

### Modern Platform (Modules 37-42)
37. **GitOps Concepts** - GitOps workflows
38. **Infrastructure as Code** - Terraform, Pulumi, CDK
39. **Kubernetes Concepts** - K8s platform patterns
40. **Multi-Tenant Platform** - Multi-tenancy patterns
41. **Multi-Cloud Platform** - Multi-cloud strategies
42. **Platform Reliability** - SRE practices

### Operations (Modules 43-47)
43. **Platform Operations** - Day-2 operations
44. **Release Engineering** - Release management
45. **Platform Testing** - Testing strategies
46. **CI/CD** - Continuous integration/deployment
47. **Platform Best Practices** - Industry best practices

### Enterprise (Modules 48-50)
48. **Production Operations** - Production runbooks
49. **Enterprise Integration** - ERP, CRM, ITSM integration
50. **Enterprise Capstone** - Complete platform integration

## Real Business Scenarios

### Self-Service Data Platform
- **Self-Service Data Lake** - Automated data lake creation
- **Self-Service Kafka Topics** - Topic provisioning with schema registry
- **Self-Service Airflow DAGs** - DAG deployment and management
- **Self-Service Databricks Workspaces** - Workspace automation
- **Self-Service Snowflake Warehouses** - Warehouse provisioning

### Self-Service AI Platform
- **Self-Service ML Projects** - MLflow project templates
- **Self-Service AI Agents** - Agent deployment and orchestration
- **Feature Store Automation** - Feature registration and serving

### Platform Services
- **Platform Provisioning** - End-to-end resource provisioning
- **Environment Automation** - Automated environment management
- **Enterprise Developer Portal** - Central developer hub
- **Executive Platform Dashboard** - C-level visibility

## End-to-End Platform Flow

```
Developer Request
    ↓
Developer Portal
    ↓
Template Selection
    ↓
Policy Validation (OPA)
    ↓
Approval Workflow (GitHub Actions)
    ↓
Infrastructure Provisioning (Terraform)
    ↓
CI/CD Pipeline (GitHub Actions)
    ↓
Deployment (ArgoCD)
    ↓
Monitoring (Prometheus, Grafana)
    ↓
Lifecycle Management
    ↓
[Governance, Audit Logging, Notifications, Rollback, Observability]
```

## Developer Experience

### Golden Paths
Pre-approved, production-ready templates for common use cases:
- Data lake with medallion architecture
- Real-time streaming pipeline
- ML training pipeline with MLflow
- Feature store with online/offline serving
- AI agent with RAG capabilities

### Platform CLI
```bash
# Install platform CLI
pip install platform-cli

# Initialize project from golden path
platform init --template data-lake --name my-data-lake

# Provision infrastructure
platform provision --env dev

# Deploy application
platform deploy --service my-service

# View logs
platform logs --service my-service --tail 100

# Check platform status
platform status
```

### Developer Dashboard
- Service catalog with usage metrics
- Provisioning history and status
- Cost tracking and budgets
- Documentation and tutorials
- Support and feedback

## Observability

### Platform Metrics
- Provisioning success/failure rates
- Deployment frequency and lead time
- Infrastructure utilization
- API latency and error rates
- Template usage statistics

### Developer Analytics
- Time to first deployment
- Self-service adoption rate
- Developer satisfaction (NPS)
- Support ticket trends
- Training completion rates

### Resource Monitoring
- CPU, memory, storage utilization
- Network throughput
- Database connection pools
- Cache hit rates
- Queue depths

## Security

### Enterprise RBAC
```yaml
# Role: Data Engineer
permissions:
  - data-platform:read
  - data-platform:write
  - airflow:read
  - airflow:write
  - kafka:read
  - kafka:write

# Role: ML Engineer
permissions:
  - ml-platform:read
  - ml-platform:write
  - feature-store:read
  - model-serving:deploy

# Role: Platform Admin
permissions:
  - '*:*'
```

### Secrets Management
- HashiCorp Vault integration
- Kubernetes sealed secrets
- Azure Key Vault / AWS Secrets Manager
- Automatic rotation policies

### Policy as Code
```rego
# Deny public S3 buckets
package platform.s3

deny[msg] {
  input.resource.type == "AWS::S3::Bucket"
  input.resource.properties.PublicAccessBlockConfiguration.BlockPublicAcls == false
  msg := "S3 buckets must block public ACLs"
}

# Require encryption at rest
package platform.encryption

deny[msg] {
  input.resource.type == "AWS::RDS::DBInstance"
  not input.resource.properties.StorageEncrypted
  msg := "RDS instances must have encryption at rest enabled"
}
```

## CI/CD

### GitHub Actions Integration
```yaml
name: Platform Validation
on:
  pull_request:
    paths:
      - 'platform/**'
      - 'services/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pytest tests/
      - run: ruff check platform/ services/
      - run: mypy platform/ services/
```

### GitOps with ArgoCD
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-services
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/platform-gitops
    targetRevision: HEAD
    path: kubernetes/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: platform-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Testing

### Test Coverage
- **Unit Tests**: 90%+ coverage for all modules
- **Integration Tests**: API, database, service integration
- **E2E Tests**: Full platform workflows
- **Performance Tests**: Load, stress, benchmark
- **Security Tests**: SAST, DAST, dependency scanning

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=platform --cov-report=html

# Run specific test suite
pytest tests/integration/

# Run performance benchmarks
pytest tests/performance/ --benchmark-only
```

## Documentation

### Comprehensive Guides
- **Platform Architecture** - System design and patterns
- **IDP Guide** - Building internal developer platforms
- **Developer Experience** - DX best practices
- **Governance** - Policy and compliance
- **Deployment Guide** - Production deployment
- **Troubleshooting** - Common issues and solutions

### Diagrams
- Platform architecture diagrams
- Workflow diagrams
- Integration diagrams
- Data flow diagrams

## Exercises

### 100+ Platform Engineering Exercises

#### Beginner (1-33)
1. Set up local development environment
2. Create your first golden path template
3. Deploy a simple data pipeline
4. Configure RBAC for a team
5. Set up monitoring for a service
... (100 total exercises across all levels)

#### Intermediate (34-66)
34. Design multi-tenant namespace strategy
35. Implement cost allocation tags
36. Create custom platform SDK extension
... (100 total exercises)

#### Advanced (67-100)
67. Design multi-cloud disaster recovery
68. Implement advanced quota management
69. Build custom workflow engine plugin
... (100 total exercises)

## Interview Questions

### 300+ Platform Engineering Interview Questions

#### Platform Engineering Fundamentals (1-50)
1. What is platform engineering and how does it differ from DevOps?
2. Explain the concept of "paved roads" in platform engineering.
3. What are golden paths and why are they important?
... (300 total questions)

#### Categories:
- Platform Engineering Principles (50 questions)
- IDP Design (50 questions)
- Self-Service Infrastructure (50 questions)
- Developer Experience (50 questions)
- Platform APIs & SDK (50 questions)
- Governance & Security (50 questions)
- Observability (50 questions)
- Enterprise Integration (50 questions)
- Scenario-Based (300+ questions)

## Quality Standards

### Code Quality
- **Python 3.13+** with type hints
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking
- **pytest** for testing
- Structured logging throughout

### Infrastructure Quality
- **Terraform** modules with validation
- **Kubernetes** manifests with kustomize
- **Helm** charts for complex deployments
- **GitOps** for declarative management
- Comprehensive documentation

### Documentation Quality
- Professional README for every module
- Architecture diagrams for all services
- API reference with OpenAPI specs
- Troubleshooting guides
- Runbooks for operations

## Integration with Previous Projects

This project integrates with and builds upon:

- **Project 01-06**: Python fundamentals, ETL frameworks
- **Project 07-10**: PySpark, Delta Lake, Databricks
- **Project 11-13**: Airflow, Kafka, Streaming
- **Project 14-15**: dbt, Snowflake
- **Project 16-18**: Azure Data Factory, AWS Glue, EMR
- **Project 20**: Modern Data Platform Capstone
- **Project 21**: Data Mesh
- **Project 22**: Data Fabric
- **Project 23**: MLOps & Feature Platform
- **Project 24**: Real-Time AI Platform
- **Project 25**: Data Platform SRE

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../../LICENSE)

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/sathiyamurthyr/production-data-engineering-projects/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sathiyamurthyr/production-data-engineering-projects/discussions)

## Roadmap

See [ROADMAP.md](../../ROADMAP.md) for project roadmap.

---

**Built with ❤️ for the data and AI community**

**Status**: Production-Ready ✅

**Last Updated**: 2026