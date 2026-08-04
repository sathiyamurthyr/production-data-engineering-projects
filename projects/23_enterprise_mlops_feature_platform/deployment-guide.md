# MLOps Platform - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Enterprise MLOps & Feature Platform in production environments.

## Architecture Components

The platform consists of:

- **MLflow Tracking Server**: Experiment tracking and model registry
- **Feature Store**: Delta Lake (offline), Redis (online)
- **Model Serving**: FastAPI REST endpoints
- **Monitoring**: Prometheus, Grafana, Evidently AI
- **Orchestration**: Airflow for pipelines
- **Storage**: S3/ADLS for artifacts, PostgreSQL for metadata

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 8 cores | 16+ cores |
| RAM | 32 GB | 64+ GB |
| Storage | 500 GB SSD | 1+ TB SSD |

### Software Requirements

- Python 3.13+
- Docker & Docker Compose
- Kubernetes (for production)
- MLflow 2.x
- Apache Spark 3.5+
- Delta Lake 3.x
- Redis 7.x
- PostgreSQL 14+
- Neo4j (optional, for advanced lineage)

## Deployment Options

### Option 1: Docker Compose (Development)

```bash
# Clone repository
git clone <repository-url>
cd production-data-engineering-projects/projects/23_enterprise_mlops_feature_platform

# Create environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Verify services
docker-compose ps
```

### Option 2: Kubernetes (Production)

```bash
# Deploy to Kubernetes
kubectl apply -f infrastructure/kubernetes/namespace.yaml
kubectl apply -f infrastructure/kubernetes/configmap.yaml
kubectl apply -f infrastructure/kubernetes/secrets.yaml
kubectl apply -f infrastructure/kubernetes/mlflow.yaml
kubectl apply -f infrastructure/kubernetes/feature-store.yaml
kubectl apply -f infrastructure/kubernetes/model-serving.yaml
kubectl apply -f infrastructure/kubernetes/monitoring.yaml
```

### Option 3: Terraform (Cloud)

```bash
# Initialize Terraform
cd infrastructure/terraform
terraform init

# Plan deployment
terraform plan -var-file=../configs/prod.tfvars

# Apply deployment
terraform apply -var-file=../configs/prod.tfvars
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# MLflow
MLFLOW_TRACKING_URI=postgresql://mlflow:password@postgres:5432/mlflow
MLFLOW_ARTIFACT_ROOT=s3://mlflow-artifacts

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mlflow
POSTGRES_USER=mlflow
POSTGRES_PASSWORD=<secure-password>

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<secure-password>

# Feature Store
FEATURE_STORE_OFFLINE_PATH=s3://feature-store/offline
FEATURE_STORE_ONLINE_REDIS_URI=redis://redis:6379

# Model Serving
MODEL_SERVING_HOST=0.0.0.0
MODEL_SERVING_PORT=8000
MODEL_SERVING_WORKERS=4

# Spark
SPARK_MASTER=local[*]
SPARK_HOME=/opt/spark

# Monitoring
PROMETHEUS_PORT=8001
GRAFANA_PORT=3000
```

### Platform Configuration

Create `configs/platform.yaml`:

```yaml
platform:
  name: "Enterprise MLOps Platform"
  version: "1.0.0"
  environment: production

mlflow:
  tracking_uri: postgresql://mlflow:password@postgres:5432/mlflow
  artifact_root: s3://mlflow-artifacts
  experiment_name: "production"

feature_store:
  offline:
    type: delta_lake
    path: s3://feature-store/offline
    catalog: "gold"
  
  online:
    type: redis
    host: redis
    port: 6379
    ttl: 86400  # 24 hours

model_serving:
  host: 0.0.0.0
  port: 8000
  workers: 4
  timeout: 30
  max_batch_size: 100

training:
  spark_master: local[*]
  driver_memory: 8g
  executor_memory: 16g
  executor_cores: 4
  num_executors: 10

monitoring:
  prometheus_port: 8001
  grafana_port: 3000
  drift_threshold: 0.05
  alert_email: mlops-alerts@example.com

pipelines:
  scheduler: airflow
  max_concurrent_runs: 5
  retry_attempts: 3
  retry_delay: 300  # seconds
```

## Docker Deployment

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  mlflow:
    image: mlflow:2.10.0
    ports:
      - "5000:5000"
    environment:
      - MLFLOW_TRACKING_URI=postgresql://mlflow:password@postgres:5432/mlflow
      - MLFLOW_ARTIFACT_ROOT=s3://mlflow-artifacts
    volumes:
      - mlflow-artifacts:/mlflow-artifacts
    depends_on:
      - postgres
    command: mlflow server --backend-store-uri postgresql://mlflow:password@postgres:5432/mlflow --default-artifact-root s3://mlflow-artifacts --host 0.0.0.0 --port 5000
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=mlflow
      - POSTGRES_USER=mlflow
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  feature-store:
    image: feature-store:latest
    ports:
      - "8002:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OFFLINE_STORE_PATH=s3://feature-store/offline
    depends_on:
      - redis
    restart: unless-stopped

  model-serving:
    image: model-serving:latest
    ports:
      - "8000:8000"
      - "8001:8001"
    environment:
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - REDIS_HOST=redis
    depends_on:
      - mlflow
      - redis
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
  mlflow-artifacts:
  grafana-data:
```

### Build and Start

```bash
docker-compose up -d --build

# Check logs
docker-compose logs -f mlflow
docker-compose logs -f model-serving

# Stop services
docker-compose down
```

## Kubernetes Deployment

### Namespace

```yaml
# infrastructure/kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mlops
  labels:
    name: mlops
```

### MLflow Deployment

```yaml
# infrastructure/kubernetes/mlflow.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow
  namespace: mlops
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mlflow
  template:
    metadata:
      labels:
        app: mlflow
    spec:
      containers:
      - name: mlflow
        image: mlflow:2.10.0
        ports:
        - containerPort: 5000
        env:
        - name: MLFLOW_TRACKING_URI
          valueFrom:
            secretKeyRef:
              name: mlops-secrets
              key: mlflow-tracking-uri
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: mlflow
  namespace: mlops
spec:
  selector:
    app: mlflow
  ports:
  - port: 80
    targetPort: 5000
  type: ClusterIP
```

### Model Serving Deployment

```yaml
# infrastructure/kubernetes/model-serving.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: model-serving
  namespace: mlops
spec:
  replicas: 3
  selector:
    matchLabels:
      app: model-serving
  template:
    metadata:
      labels:
        app: model-serving
    spec:
      containers:
      - name: model-serving
        image: model-serving:latest
        ports:
        - containerPort: 8000
        - containerPort: 8001
        env:
        - name: MLFLOW_TRACKING_URI
          value: http://mlflow:80
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: model-serving
  namespace: mlops
spec:
  selector:
    app: model-serving
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Deploy to Kubernetes

```bash
kubectl apply -f infrastructure/kubernetes/
```

## Production Best Practices

### 1. Security

- Use secrets management (HashiCorp Vault, AWS Secrets Manager)
- Enable TLS/SSL for all endpoints
- Implement network policies
- Regular security updates
- Audit logging enabled

### 2. High Availability

- Deploy multiple replicas for MLflow and model serving
- Use load balancers
- Database replication (PostgreSQL)
- Redis cluster for caching
- Multi-zone deployment

### 3. Monitoring

```bash
# Prometheus metrics
GET http://localhost:8001/metrics

# Health check
GET http://localhost:8000/health

# MLflow UI
GET http://localhost:5000
```

### 4. Backup Strategy

```bash
# PostgreSQL backup (MLflow metadata)
pg_dump -U mlflow mlflow > mlflow_backup.sql

# MLflow artifacts backup
aws s3 sync s3://mlflow-artifacts s3://mlflow-artifacts-backup

# Feature store backup
aws s3 sync s3://feature-store s3://feature-store-backup
```

## Scaling

### Horizontal Scaling

```bash
# Scale model serving
kubectl scale deployment/model-serving --replicas=10 -n mlops

# Scale MLflow
kubectl scale deployment/mlflow --replicas=3 -n mlops
```

### Performance Tuning

```yaml
# configs/performance.yaml
model_serving:
  workers: 8
  max_connections: 1000
  timeout: 30

training:
  spark:
    executor_instances: 20
    executor_cores: 4
    executor_memory: 16g
```

## Troubleshooting

### Common Issues

1. **MLflow Connection Errors**
   ```bash
   # Check MLflow status
   curl http://localhost:5000/health
   
   # Check PostgreSQL
   kubectl logs -f deployment/mlflow -n mlops
   ```

2. **Model Loading Failures**
   ```bash
   # Check model artifacts
   aws s3 ls s3://mlflow-artifacts/
   
   # Check model serving logs
   kubectl logs -f deployment/model-serving -n mlops
   ```

3. **Feature Store Latency**
   ```bash
   # Check Redis
   redis-cli ping
   
   # Check Delta Lake
   ls -la /mnt/feature-store/offline
   ```

### Logs

```bash
# MLflow logs
docker-compose logs -f mlflow

# Model serving logs
docker-compose logs -f model-serving

# Kubernetes logs
kubectl logs -f deployment/model-serving -n mlops
```

## Maintenance

### Regular Tasks

1. **Daily**
   - Monitor model performance
   - Check drift detection alerts
   - Review prediction logs

2. **Weekly**
   - Clean up old experiments
   - Review model registry
   - Update feature definitions

3. **Monthly**
   - Security updates
   - Performance tuning
   - Capacity planning

### Updates

```bash
# Rolling update
kubectl set image deployment/model-serving model-serving=model-serving:v2.0.0 -n mlops

# Verify deployment
kubectl rollout status deployment/model-serving -n mlops

# Rollback if needed
kubectl rollout undo deployment/model-serving -n mlops
```

## Support

For issues and questions:
- Documentation: https://mlops.example.com/docs
- Issues: https://github.com/org/mlops/issues
- Email: mlops-support@example.com