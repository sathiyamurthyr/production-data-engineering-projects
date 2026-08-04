# Deployment Guide

## Overview

This guide describes the deployment process for the Enterprise Data Mesh platform across different environments.

## Prerequisites

- Python 3.13+
- Terraform 1.5+
- Docker & Docker Compose
- Cloud provider account (Azure/AWS/GCP)
- Kubernetes cluster (AKS/EKS/GKE)
- Service principal credentials

## Environment Setup

### Development

```bash
# Clone repository
git clone https://github.com/org/data-mesh-platform.git
cd projects/21_enterprise_data_mesh

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deploy local infrastructure
cd infrastructure/terraform
terraform init -backend-config="dev.backend"
terraform apply -var-file="../configs/dev.tfvars"
```

### Staging

```bash
# Deploy staging infrastructure
terraform init -backend-config="staging.backend"
terraform apply -var-file="../configs/staging.tfvars"

# Deploy domain products
./scripts/deploy-domains.sh --env staging
```

### Production

```bash
# Deploy production infrastructure
terraform init -backend-config="prod.backend"
terraform apply -var-file="../configs/prod.tfvars"

# Deploy all domains
./scripts/deploy-domains.sh --env prod --all
```

## Infrastructure Deployment

### Terraform Structure

```
infrastructure/
├── terraform/
│   ├── modules/
│   │   ├── domain/
│   │   ├── platform/
│   │   └── shared/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── configs/
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── prod.tfvars
```

### Deploy Platform Services

```hcl
module "platform" {
  source = "./modules/platform"

  environment = var.environment
  region      = var.region
  tags        = var.tags
}

module "domains" {
  for_each = var.domains

  source = "./modules/domain"

  domain_name = each.key
  domain_config = each.value
  shared_services = module.shared_services
}
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
name: Data Mesh CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run unit tests
        run: pytest tests/unit

      - name: Validate contracts
        run: python -m scripts.validate_contracts

      - name: Check governance
        run: python -m scripts.governance_check

  deploy:
    needs: validate
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to platform
        run: |
          cd infrastructure/terraform
          terraform init
          terraform apply -auto-approve

      - name: Deploy data products
        run: |
          ./scripts/deploy_products.sh --env prod
```

## Domain Deployment

### Automated Deployment Script

```bash
#!/bin/bash
# deploy-domains.sh

ENV=${1:-dev}
DOMAIN=${2:-all}

if [ "$DOMAIN" == "all" ]; then
  for domain in customer payments finance marketing retail healthcare; do
    deploy_domain $domain $ENV
  done
else
  deploy_domain $DOMAIN $ENV
fi

deploy_domain() {
  local domain=$1
  local env=$2

  echo "Deploying $domain domain to $env"

  # Validate contract
  python scripts/validate_contract.py --domain $domain --env $env

  # Run tests
  pytest tests/domains/$domain

  # Deploy pipeline
  dbt run --profiles-dir configs/$env --target $env

  # Register in catalog
  python scripts/register_product.py --domain $domain --env $env
}
```

## Configuration Management

### Environment Variables

```bash
# .env.production
DOMAIN_STORAGE_ACCOUNT=datameshprodstorage
CATALOG_SERVICE_URL=https://catalog.prod.datamesh.internal
GOVERNANCE_SERVICE_URL=https://governance.prod.datamesh.internal
KAFKA_BOOTSTRAP_SERVERS=kafka.prod.datamesh.internal:9092
SPARK_POOL=datamesh-prod-pool
```

### Secrets Management

```hcl
resource "azurerm_key_vault" "domain_secrets" {
  name = "${var.domain_name}-secrets"
  resource_group_name = var.resource_group

  sku_name = "standard"
}

resource "azurerm_key_vault_secret" "database_connection" {
  name = "db-connection-string"
  value = var.db_connection_string
  key_vault_id = azurerm_key_vault.domain_secrets.id
}
```

## Monitoring Setup

### Deploy Monitoring

```bash
# Deploy Prometheus
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --create-namespace

# Deploy Grafana dashboards
kubectl apply -f monitoring/dashboards/

# Configure alertmanager
kubectl apply -f monitoring/alerts/
```

## Rollback Procedures

### Automated Rollback

```bash
# Rollback to previous version
./scripts/rollback.sh --domain customer --version 1.2.3

# Rollback infrastructure
cd infrastructure/terraform
terraform apply -var-file="../configs/rollback.tfvars"
```

## Disaster Recovery

### Backup Strategy

```bash
# Daily backups
./scripts/backup.sh --type delta --domain all

# Weekly full backup
./scripts/backup.sh --type full --retention 30
```

## Verification

### Health Checks

```bash
# Verify deployment
./scripts/verify_deployment.sh --env prod

# Check domain health
./scripts/domain_health.sh --domain customer
```

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for common issues.