# Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Enterprise Platform Engineering IDP to various environments (development, staging, production).

## Prerequisites

### Required Tools

```bash
# Install required tools
# Python 3.13+
python --version  # Should show 3.13.x

# Terraform >= 1.5.0
terraform version

# Kubernetes CLI
kubectl version --client

# Docker
docker --version

# Git
git --version

# Azure CLI (for Azure deployments)
az version
```

### Required Accounts & Access

- Azure subscription with contributor access
- GitHub organization with admin access
- Docker Hub or ACR access
- Domain name for platform API

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/sathiyamurthyr/production-data-engineering-projects.git
cd production-data-engineering-projects/projects/26_enterprise_platform_engineering
```

### 2. Configure Terraform Backend

```bash
# Create Terraform state storage
az group create --name platform-terraform-rg --location eastus

# Create storage account for Terraform state
az storage account create \
  --name platformtfstate \
  --resource-group platform-terraform-rg \
  --location eastus \
  --sku Standard_GRS \
  --encryption-services blob

# Create container
az storage container create \
  --name tfstate \
  --account-name platformtfstate
```

### 3. Configure Variables

```bash
# Copy example variables
cp terraform/environments/dev.tfvars.example terraform/environments/dev.tfvars

# Edit variables
vim terraform/environments/dev.tfvars
```

**dev.tfvars**:
```hcl
environment = "dev"
location    = "East US"

kubernetes_version = "1.28"

system_node_count  = 2
system_node_vm_size = "Standard_D4s_v5"
user_node_count    = 3
user_node_vm_size  = "Standard_D8s_v5"

postgresql_sku = "B_Standard_B4ms"
redis_capacity = 2
acr_sku        = "Premium"

tags = {
  Environment = "dev"
  Project     = "Enterprise Platform"
  ManagedBy   = "Terraform"
  CostCenter  = "Platform Engineering"
}
```

## Deployment Options

### Option 1: Azure Deployment (Recommended)

#### Step 1: Deploy Infrastructure with Terraform

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan deployment
terraform plan \
  -var-file=environments/dev.tfvars \
  -out=tfplan

# Review the plan
terraform show tfplan

# Apply the plan
terraform apply tfplan

# Save outputs
terraform output > ../configs/terraform-outputs.json
```

**Expected Output**:
```
Outputs:

kubernetes_cluster_name = "platform-aks-dev"
kubernetes_cluster_host = "https://..."
postgresql_server_fqdn = "platform-postgres-dev.postgres.database.azure.com"
key_vault_name = "platform-vault-dev"
redis_cache_host = "platform-redis-dev.redis.cache.windows.net"
container_registry_login_server = "platformacrdev.azurecr.io"
```

#### Step 2: Configure Kubernetes

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group enterprise-platform-rg \
  --name platform-aks-dev \
  --overwrite-existing

# Verify connection
kubectl get nodes

# Create namespaces
kubectl apply -f kubernetes/base/namespaces.yaml

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# Install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=300s
```

#### Step 3: Deploy Platform Services

```bash
# Create secrets
kubectl create secret generic platform-secrets \
  --namespace=platform-system \
  --from-literal=database-url=$(terraform output -raw platform_services_connection_string) \
  --from-literal=redis-url=$(terraform output -raw redis_cache_host) \
  --from-literal=jwt-secret=$(openssl rand -base64 32) \
  --from-literal=vault-url=$(terraform output -raw key_vault_uri)

# Deploy platform services
kubectl apply -f kubernetes/base/platform-system/

# Verify deployment
kubectl get pods -n platform-system

# Expected output:
# NAME                                    READY   STATUS    RESTARTS   AGE
# platform-api-7d9f4b8b5c-x2k4p          1/1     Running   0          2m
# platform-worker-5c8f7d9b6c-p3l2m       1/1     Running   0          2m
# platform-monitoring-9f8d7b6c5-x1y2z    1/1     Running   0          2m
```

#### Step 4: Configure DNS

```bash
# Get ingress IP
kubectl get svc -n ingress-nginx

# Create DNS A record
# Name: platform
# IP: <ingress-ip>
```

#### Step 5: Deploy with ArgoCD (GitOps)

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s

# Get admin password
argocd admin initial-password -n argocd

# Create ArgoCD application
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-services
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/sathiyamurthyr/production-data-engineering-projects
    targetRevision: HEAD
    path: projects/26_enterprise_platform_engineering/kubernetes/overlays/dev
  destination:
    server: https://kubernetes.default.svc
    namespace: platform-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF
```

### Option 2: Docker Compose (Development)

For local development, use Docker Compose:

```bash
# Start all services
docker-compose up -d

# Verify services
docker-compose ps

# Expected output:
# Name                     Command               State           Ports
# platform-api       uvicorn main:app --host ...   Up      0.0.0.0:8000->8000/tcp
# platform-postgres  docker-entrypoint.sh postgres   Up      0.0.0.0:5432->5432/tcp
# platform-redis     docker-entrypoint.sh redis ...   Up      0.0.0.0:6379->6379/tcp
# platform-vault     vault server -config=/vault ...   Up      0.0.0.0:8200->8200/tcp

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_USER: platform
      POSTGRES_PASSWORD: platform123
      POSTGRES_DB: platform
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  vault:
    image: vault:1.15
    cap_add:
      - IPC_LOCK
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: root
    ports:
      - "8200:8200"

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://platform:platform123@postgres:5432/platform
      REDIS_URL: redis://redis:6379
      VAULT_URL: http://vault:8200
    depends_on:
      - postgres
      - redis
      - vault

volumes:
  postgres-data:
  redis-data:
```

### Option 3: Helm Chart (Kubernetes)

```bash
# Add Helm repository
helm repo add platform https://charts.platform.example.com
helm repo update

# Install platform
helm install platform platform/platform \
  --namespace platform-system \
  --create-namespace \
  --values helm/values-dev.yaml

# Upgrade
helm upgrade platform platform/platform \
  --namespace platform-system \
  --values helm/values-dev.yaml

# Rollback
helm rollback platform 1 -n platform-system
```

## Configuration

### Environment Variables

```bash
# .env file
DATABASE_URL=postgresql://user:pass@host:5432/platform
REDIS_URL=redis://host:6379
VAULT_URL=https://vault.example.com
JWT_SECRET_KEY=your-secret-key
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
LOG_LEVEL=INFO
ENVIRONMENT=dev
```

### Platform Configuration

```yaml
# configs/platform.yaml
platform:
  name: "Enterprise Platform"
  version: "1.0.0"
  environment: "dev"

database:
  pool_size: 20
  max_overflow: 10
  echo: false

cache:
  ttl: 3600
  prefix: "platform:"

auth:
  jwt_expiry: 1800  # 30 minutes
  refresh_token_expiry: 604800  # 7 days
  algorithm: "HS256"

provisioning:
  max_concurrent: 10
  timeout: 600  # 10 minutes
  retry_attempts: 3

templates:
  path: "/templates"
  cache_ttl: 300  # 5 minutes

monitoring:
  metrics_enabled: true
  tracing_enabled: true
  log_level: "INFO"
```

## Verification

### Health Checks

```bash
# Check platform health
curl https://platform.example.com/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "vault": {"status": "healthy"}
  },
  "version": "1.0.0"
}

# Check API health
curl https://platform.example.com/api/v1/health

# Check Kubernetes pods
kubectl get pods -n platform-system

# Check services
kubectl get svc -n platform-system

# Check ingress
kubectl get ingress -n platform-system
```

### Functional Tests

```bash
# Run test suite
pytest tests/ -v

# Run integration tests
pytest tests/integration/ -v

# Test API endpoints
curl -X POST https://platform.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Test provisioning
curl -X POST https://platform.example.com/api/v1/templates/data-lake-medallion/provision \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "project_name": "test-lake",
      "environment": "dev"
    },
    "team": "data-team"
  }'
```

## Scaling

### Horizontal Scaling

```bash
# Scale API servers
kubectl scale deployment/platform-api -n platform-system --replicas=5

# Scale workers
kubectl scale deployment/platform-worker -n platform-system --replicas=10

# Verify scaling
kubectl get pods -n platform-system
```

### Auto-scaling Configuration

```yaml
# kubernetes/base/platform-system/api-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: platform-api-hpa
  namespace: platform-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: platform-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Monitoring

### Prometheus Setup

```bash
# Install Prometheus
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --create-namespace

# Verify
kubectl get pods -n monitoring
```

### Grafana Dashboards

```bash
# Install Grafana
helm install grafana grafana/grafana \
  --namespace monitoring \
  --create-namespace \
  --set adminPassword=admin123

# Port-forward
kubectl port-forward -n monitoring svc/grafana 3000:80

# Access at http://localhost:3000
# Username: admin
# Password: admin123
```

### Logging

```bash
# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --create-namespace

# Install Fluentd
helm install fluentd fluent/fluentd \
  --namespace logging
```

## Backup & Recovery

### Database Backups

```bash
# Manual backup
kubectl exec -n platform-system platform-postgres-0 -- \
  pg_dump -U platform platform > backup.sql

# Automated backups (configured in Terraform)
# - Daily automated backups
# - 7-day retention
# - Geo-redundant storage (production)

# Restore
kubectl exec -i -n platform-system platform-postgres-0 -- \
  psql -U platform platform < backup.sql
```

### Terraform State Backup

```bash
# Terraform state is stored in Azure Storage with:
# - Geo-redundant storage (GRS)
# - Soft delete enabled
# - Versioning enabled

# Export state
terraform state pull > backup.tfstate

# Import state
terraform state push backup.tfstate
```

## Troubleshooting

### Common Issues

**Issue**: Pods stuck in Pending state

**Solution**:
```bash
# Check pod events
kubectl describe pod <pod-name> -n platform-system

# Common causes:
# - Insufficient resources
# - Node selector mismatch
# - PVC pending

# Check node resources
kubectl describe nodes

# Check PVC
kubectl get pvc -n platform-system
```

**Issue**: Services can't connect to database

**Solution**:
```bash
# Check secrets
kubectl get secrets -n platform-system

# Verify database URL
kubectl exec -n platform-system <pod-name> -- env | grep DATABASE_URL

# Test connectivity
kubectl exec -n platform-system <pod-name> -- nc -zv <db-host> 5432
```

**Issue**: Ingress not working

**Solution**:
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress
kubectl describe ingress -n platform-system

# Check logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

## Rollback

### Application Rollback

```bash
# kubectl rollout
kubectl rollout undo deployment/platform-api -n platform-system
kubectl rollout undo deployment/platform-worker -n platform-system

# Verify
kubectl rollout status deployment/platform-api -n platform-system
```

### Terraform Rollback

```bash
# List state versions
terraform state list

# Rollback to previous state
terraform state push previous-state.tfstate

# Or use Terraform Cloud/Enterprise for state versioning
```

### Helm Rollback

```bash
# View release history
helm history platform -n platform-system

# Rollback to previous version
helm rollback platform 1 -n platform-system

# Rollback to specific version
helm rollback platform 3 -n platform-system
```

## Maintenance

### Regular Tasks

**Daily**:
- Review platform health dashboard
- Check for failed provisioning requests
- Monitor error rates

**Weekly**:
- Review cost reports
- Update dependencies (security patches)
- Review audit logs

**Monthly**:
- Terraform state cleanup
- Kubernetes node updates
- Backup verification
- Performance review

### Upgrades

```bash
# Upgrade platform services
git pull origin main
cd terraform
terraform apply -var-file=environments/prod.tfvars

# Rolling update
kubectl rollout restart deployment/platform-api -n platform-system
kubectl rollout restart deployment/platform-worker -n platform-system

# Verify
kubectl rollout status deployment/platform-api -n platform-system
```

## Security

### Certificate Management

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: platform@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
EOF

# Certificate auto-renewal is handled by cert-manager
```

### Secrets Rotation

```bash
# Rotate JWT secret
kubectl create secret generic platform-secrets \
  --namespace=platform-system \
  --from-literal=jwt-secret=$(openssl rand -base64 32) \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new secret
kubectl rollout restart deployment/platform-api -n platform-system
```

## References

- [Platform Architecture](architecture.md)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io)