# Self-Service Data Platform Guide

## Overview

The self-service data platform provides domain teams with standardized tools and interfaces to build, deploy, and manage data products independently while ensuring compliance with enterprise standards.

## Platform Services

### 1. Domain Provisioning

Automated provisioning of domain infrastructure:

```yaml
domain_provisioning:
  compute:
    - cluster_size: small|medium|large
    - auto_scaling: enabled
    - serverless: true
  storage:
    - bronze_zone: delta_lake
    - silver_zone: delta_lake
    - gold_zone: delta_lake
  networking:
    - vnet_isolation: true
    - dns_zone: domain_name
```

### 2. Project Templates

Standard templates for data product development:

```
templates/
├── streaming-product/
│   ├── pipeline/
│   ├── quality/
│   ├── contract/
│   └── monitoring/
├── batch-product/
│   ├── dag/
│   ├── dbt/
│   ├── quality/
│   └── monitoring/
└── lakehouse-product/
    ├── bronze_job/
    ├── silver_job/
    ├── gold_job/
    └── quality/
```

### 3. CI/CD Templates

Pre-built pipelines for different product types:

```yaml
# streaming-product-pipeline.yml
name: Streaming Product CI/CD
on:
  push:
    branches: [main, develop]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - quality_tests
      - contract_tests
      - security_scan
  deploy:
    needs: validate
    steps:
      - deploy_bronze
      - deploy_silver
      - deploy_gold
      - register_catalog
```

### 4. Metadata Templates

Standard metadata schemas:

```json
{
  "data_product": {
    "name": "string",
    "domain": "string",
    "owner": "string",
    "version": "semver",
    "sla": {
      "freshness": "duration",
      "availability": "percentage"
    },
    "quality": {
      "expectations": "list"
    }
  }
}
```

### 5. Quality Templates

Pre-configured quality suites:

- completeness_check
- uniqueness_check
- referential_integrity
- freshness_check
- schema_evolution

### 6. Monitoring Templates

Standard dashboards and alerts:

- freshness_dashboard
- quality_dashboard
- consumer_analytics
- sla_compliance
- cost_allocation

## Platform SDK

### Installation

```bash
pip install data-mesh-platform-sdk
```

### Usage

```python
from data_mesh_platform.sdk import DataProductClient

# Initialize client
client = DataProductClient(
    domain="customer",
    environment="prod"
)

# Register data product
client.register_product(
    name="customer_360",
    version="1.0.0",
    schema=schema_definition
)

# Deploy pipeline
client.deploy_pipeline(
    pipeline_name="customer_360_pipeline",
    template="batch-product"
)
```

## APIs

### Catalog API

```http
GET /api/v1/catalog/products
GET /api/v1/catalog/products/{id}
POST /api/v1/catalog/products
PUT /api/v1/catalog/products/{id}
DELETE /api/v1/catalog/products/{id}
```

### Governance API

```http
GET /api/v1/governance/policies
POST /api/v1/governance/validate
GET /api/v1/governance/compliance/{domain}
```

### Monitoring API

```http
GET /api/v1/monitoring/health
GET /api/v1/monitoring/sla
GET /api/v1/monitoring/quality
```

## CLI Tools

```bash
# Provision domain
data-mesh provision domain --name customer --template standard

# Register product
data-mesh register product --spec product.yaml

# Run tests
data-mesh test product --all

# Deploy
data-mesh deploy product --env prod
```

## Self-Service Portal

Web-based interface for:

- Product discovery
- Documentation access
- Monitoring dashboards
- Access requests
- Cost analytics

## Infrastructure Patterns

### Multi-Cloud Support

```hcl
module "domain_infrastructure" {
  source = "./modules/domain"

  domain_name     = var.domain_name
  cloud_provider  = var.cloud_provider  # azure, aws, gcp
  environment     = var.environment
}
```

### Cost-Optimized Compute

- Serverless Spark pools
- Auto-scaling configurations
- Spot instance policies
- Resource scheduling

## Security Integration

### Authentication

- SSO/SAML integration
- API key management
- Service principal auth
- Token rotation

### Authorization

- RBAC by domain
- ABAC by attributes
- Just-in-time access
- Approval workflows

## Observability

### Standard Metrics

| Metric | Type | Description |
|--------|------|-------------|
| freshness | gauge | Data freshness duration |
| quality_score | gauge | Quality percentage |
| consumer_count | gauge | Active consumers |
| cost | gauge | Resource costs |

### Alert Templates

```yaml
alerts:
  - name: data_freshness_breach
    condition: freshness > sla_threshold
    severity: warning
    notification: slack, email, pagerduty
```

## Best Practices

1. Use provided templates for consistency
2. Validate contracts before deployment
3. Monitor SLAs continuously
4. Document all products
5. Follow naming conventions
6. Implement proper error handling