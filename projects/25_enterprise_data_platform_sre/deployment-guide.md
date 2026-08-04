# Enterprise Data Platform SRE - Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Enterprise Data Platform SRE in production environments.

## Prerequisites

### System Requirements

- **Python**: 3.13+
- **Memory**: 8GB minimum (16GB recommended)
- **Storage**: 50GB minimum
- **Network**: Stable internet connection for package downloads

### Dependencies

```bash
# Install system dependencies
# On macOS
brew install python@3.13

# On Ubuntu
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv

# On RHEL/CentOS
sudo yum install -y python39
```

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/your-org/production-data-engineering-projects.git
cd production-data-engineering-projects/projects/25_enterprise_data_platform_sre
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 5. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 6. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=monitoring --cov=incident --cov=reliability --cov=automation --cov=capacity --cov=dr --cov=chaos --cov=runbooks --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Configuration

### Environment Variables

```env
# Monitoring Configuration
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000
ALERT_MANAGER_URL=http://localhost:9093

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sre_platform
POSTGRES_USER=sre_user
POSTGRES_PASSWORD=<SECRET_3dc5b8f1>ORD

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Integration Configuration
AIRFLOW_URL=http://localhost:8080
KAFKA_BROKERS=localhost:9092
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
SNOWFLAKE_ACCOUNT=your-account
AWS_REGION=us-east-1

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/sre-platform/app.log

# Security
SECRET_KEY=<your-secret-key>
ENCRYPTION_KEY=<your-encryption-key>
```

### Configuration Files

#### Monitoring Configuration

```yaml
# config/monitoring.yaml

metrics:
  collection_interval: 30s
  retention_days: 90
  batch_size: 100

golden_signals:
  latency:
    buckets: [50, 100, 200, 500, 1000, 2000, 5000]
  traffic:
    window: 1m
  errors:
    threshold: 0.05
  saturation:
    thresholds:
      cpu: 80
      memory: 85
      disk: 90

alerting:
  evaluation_interval: 30s
  deduplication_window: 5m
  escalation_timeout: 15m
```

#### Incident Management Configuration

```yaml
# config/incidents.yaml

severity_levels:
  sev1:
    response_time: 5m
    escalation_time: 10m
    auto_create_postmortem: true
  sev2:
    response_time: 15m
    escalation_time: 30m
    auto_create_postmortem: true
  sev3:
    response_time: 1h
    escalation_time: 2h
    auto_create_postmortem: false
  sev4:
    response_time: 24h
    escalation_time: 48h
    auto_create_postmortem: false

notifications:
  channels:
    - slack
    - pagerduty
    - email
  on_call_rotation: data-platform-oncall
```

#### SLO Configuration

```yaml
# config/slo.yaml

slos:
  - name: pipeline_availability
    target: 99.5
    window: 30d
    alert_threshold: 10
    category: availability
  
  - name: pipeline_latency
    target: 95.0
    window: 7d
    alert_threshold: 5
    category: latency
    unit: percent

error_budgets:
  burn_rate_alert_threshold: 10.0
  budget_critical_threshold: 20.0
```

## Deployment Options

### Option 1: Local Development

```bash
# Start all services
docker-compose up -d

# Run application
python -m sre_platform.main

# Access services
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
# - Alert Manager: http://localhost:9093
```

### Option 2: Docker Deployment

```bash
# Build Docker image
docker build -t sre-platform:latest .

# Run container
docker run -d \
  --name sre-platform \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  sre-platform:latest
```

### Option 3: Kubernetes Deployment

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl get pods -n sre-platform
kubectl get services -n sre-platform
```

### Option 4: Helm Chart

```bash
# Add Helm repository
helm repo add sre-platform https://charts.your-org.com

# Install chart
helm install sre-platform sre-platform/sre-platform \
  --namespace sre-platform \
  --create-namespace \
  --values values.yaml

# Upgrade
helm upgrade sre-platform sre-platform/sre-platform \
  --namespace sre-platform \
  --values values.yaml
```

## Production Deployment

### 1. Infrastructure Setup

```bash
# Create namespace
kubectl create namespace sre-platform

# Create secrets
kubectl create secret generic sre-secrets \
  --namespace sre-platform \
  --from-literal=postgres-password=<SECRET_3dc5b8f1>ORD \
  --from-literal=redis-password= \
  --from-literal=secret-key=<your-secret-key>

# Create configmap
kubectl create configmap sre-config \
  --namespace sre-platform \
  --from-file=config/
```

### 2. Deploy Application

```bash
# Deploy using kubectl
kubectl apply -f k8s/

# Or using Helm
helm install sre-platform ./helm/sre-platform \
  --namespace sre-platform \
  --values helm/values-prod.yaml
```

### 3. Verify Deployment

```bash
# Check pod status
kubectl get pods -n sre-platform

# Check logs
kubectl logs -f deployment/sre-platform -n sre-platform

# Check service
kubectl get services -n sre-platform

# Test health endpoint
curl http://sre-platform:8080/health
```

### 4. Configure Monitoring

```bash
# Import Grafana dashboards
curl -X POST \
  http://admin:<SECRET_1e8b3685>@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/dashboards/platform_health.json

# Configure Prometheus
# Add scrape configs to prometheus.yml
```

## Scaling

### Horizontal Scaling

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sre-platform-hpa
  namespace: sre-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sre-platform
  minReplicas: 3
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

### Database Scaling

```bash
# Scale PostgreSQL
kubectl scale statefulset postgresql --replicas=3 -n sre-platform

# Scale Redis
kubectl scale statefulset redis --replicas=3 -n sre-platform
```

## Backup and Recovery

### Database Backups

```bash
# Create backup job
kubectl apply -f k8s/backup-job.yaml

# Verify backup
kubectl get jobs -n sre-platform

# Restore from backup
kubectl apply -f k8s/restore-job.yaml
```

### Configuration Backups

```bash
# Export configurations
kubectl get configmap sre-config -n sre-platform -o yaml > backup-configmap.yaml
kubectl get secrets sre-secrets -n sre-platform -o yaml > backup-secrets.yaml

# Store in secure location
aws s3 cp backup-configmap.yaml s3://your-backup-bucket/
aws s3 cp backup-secrets.yaml s3://your-backup-bucket/
```

## Security

### TLS Configuration

```bash
# Generate certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=sre-platform/O=YourOrg"

# Create secret
kubectl create secret tls sre-platform-tls \
  --namespace sre-platform \
  --key=tls.key \
  --cert=tls.crt
```

### Network Policies

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sre-platform-netpol
  namespace: sre-platform
spec:
  podSelector:
    matchLabels:
      app: sre-platform
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: postgresql
      ports:
        - protocol: TCP
          port: 5432
```

## Monitoring

### Health Checks

```bash
# Liveness probe
curl http://sre-platform:8080/health/live

# Readiness probe
curl http://sre-platform:8080/health/ready

# Metrics endpoint
curl http://sre-platform:8080/metrics
```

### Logs

```bash
# View application logs
kubectl logs -f deployment/sre-platform -n sre-platform

# View with timestamp
kubectl logs -f deployment/sre-platform -n sre-platform --timestamps=true

# Filter logs
kubectl logs -f deployment/sre-platform -n sre-platform | grep ERROR
```

## Troubleshooting

### Common Issues

#### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n sre-platform

# Check events
kubectl get events -n sre-platform --sort-by='.lastTimestamp'

# Common causes:
# - Image pull failure: Check image name and registry credentials
# - Resource constraints: Check resource limits
# - Configuration errors: Check configmap and secrets
```

#### High Memory Usage

```bash
# Check memory usage
kubectl top pods -n sre-platform

# Increase memory limit
kubectl patch deployment sre-platform -n sre-platform \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"sre-platform","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
```

#### Database Connection Issues

```bash
# Test database connection
kubectl exec -it <pod-name> -n sre-platform -- psql -h postgresql -U sre_user

# Check connection pool
kubectl logs <pod-name> -n sre-platform | grep "connection pool"
```

## Maintenance

### Updates

```bash
# Rolling update
kubectl set image deployment/sre-platform \
  sre-platform=sre-platform:1.2.0 \
  -n sre-platform

# Rollback
kubectl rollout undo deployment/sre-platform -n sre-platform

# Check rollout status
kubectl rollout status deployment/sre-platform -n sre-platform
```

### Cleanup

```bash
# Clean up old backups
kubectl create job --from=cronjob/backup-cleanup cleanup-old-backups -n sre-platform

# Archive old metrics
python scripts/archive_metrics.py --days 90
```

## Performance Tuning

### Database Optimization

```sql
-- Optimize PostgreSQL
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
SELECT pg_reload_conf();
```

### Application Tuning

```yaml
# Application configuration
app:
  workers: 4
  threads: 8
  max_connections: 100
  connection_timeout: 30s
  request_timeout: 60s

# Connection pool
pool:
  min_size: 10
  max_size: 50
  timeout: 30
```

## Backup Strategy

### Database Backups

- **Frequency**: Every 6 hours
- **Retention**: 30 days
- **Type**: Full backup with incremental backups
- **Storage**: S3 with cross-region replication

### Configuration Backups

- **Frequency**: Daily
- **Retention**: 90 days
- **Storage**: Encrypted S3 bucket

### Disaster Recovery

- **RPO (Recovery Point Objective)**: 15 minutes
- **RTO (Recovery Time Objective)**: 1 hour
- **DR Region**: us-west-2
- **Failover**: Automated with manual approval

## Support

For issues and questions:
- Documentation: https://docs.your-org.com/sre-platform
- Slack: #sre-platform-support
- Email: sre-support@your-org.com