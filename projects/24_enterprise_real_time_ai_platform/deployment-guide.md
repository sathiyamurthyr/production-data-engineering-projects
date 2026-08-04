# Enterprise Real-Time AI Platform - Deployment Guide

## Deployment Overview

This guide covers production deployment of the Enterprise Real-Time AI Platform across multiple environments.

## Architecture

### Production Architecture

```
                    ┌─────────────────────────────────────────┐
                    │         Load Balancer (AWS ALB)          │
                    └─────────────────────────────────────────┘
                                    ↓
                    ┌─────────────────────────────────────────┐
                    │      API Gateway (FastAPI)               │
                    │  • Authentication                        │
                    │  • Rate Limiting                         │
                    │  • Request Routing                       │
                    └─────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────┬───────────────────────┐
        ↓                       ↓                       ↓
  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
  │   Service    │      │   Service    │      │   Service    │
  │   Instance   │      │   Instance   │      │   Instance   │
  │   (Pod 1)    │      │   (Pod 2)    │      │   (Pod 3)    │
  └─────────────┘      └─────────────┘      └─────────────┘
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────┐
        │         Message Queue (Kafka)                  │
        └───────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────────────────────────┐
        │    Vector Database (Pinecone/Weaviate)         │
        └───────────────────────────────────────────────┘
```

## Prerequisites

### Infrastructure

- Kubernetes cluster (EKS/GKE/AKS)
- PostgreSQL database
- Redis cache
- Vector database (Pinecone/Weaviate/Chroma)
- Object storage (S3/ADLS)
- Message queue (Kafka)

### Software

- Docker 20.10+
- Kubernetes 1.25+
- Helm 3.12+
- Terraform 1.5+
- kubectl

## Deployment Options

### Option 1: Docker Compose (Development)

```bash
# Clone repository
git clone <repository-url>
cd production-data-engineering-projects/projects/24_enterprise_real_time_ai_platform

# Create environment file
cp .env.example .env

# Start services
docker-compose up -d

# Verify services
docker-compose ps
```

### Option 2: Kubernetes (Production)

```bash
# Create namespace
kubectl create namespace ai-platform

# Deploy with Helm
helm install ai-platform ./helm/ai-platform \
  --namespace ai-platform \
  --values helm/values/production.yaml

# Verify deployment
kubectl get pods -n ai-platform
```

### Option 3: Terraform (Infrastructure as Code)

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="production.tfvars"

# Apply changes
terraform apply -var-file="production.tfvars"
```

## Configuration

### Environment Variables

```bash
# .env file
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...

# Vector Database
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...
PINECONE_INDEX_NAME=ai-platform

# Database
DATABASE_URL=postgresql://user:pass@host:5432/ai_platform
REDIS_URL=redis://redis:6379/0

# Storage
S3_BUCKET=ai-platform-documents
S3_REGION=us-west-2

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_DOCUMENTS=documents
KAFKA_TOPIC_EMBEDDINGS=embeddings

# Monitoring
PROMETHEUS_ENDPOINT=http://prometheus:9090
GRAFANA_ENDPOINT=http://grafana:3000
LANGSMITH_API_KEY=...

# Security
JWT_SECRET_KEY=...
ENCRYPTION_KEY=...
```

### Kubernetes Configuration

```yaml
# helm/ai-platform/values.yaml

replicaCount: 3

image:
  repository: ai-platform
  tag: latest
  pullPolicy: Always

resources:
  requests:
    cpu: "1"
    memory: "2Gi"
  limits:
    cpu: "4"
    memory: "8Gi"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

# Vector database
vectorDB:
  enabled: true
  type: pinecone

# Monitoring
monitoring:
  enabled: true
  prometheus: true
  grafana: true
  langsmith: true
```

## Service Deployment

### 1. AI Gateway

```bash
# Deploy API Gateway
kubectl apply -f kubernetes/api-gateway.yaml

# Verify deployment
kubectl get deployment ai-gateway -n ai-platform
kubectl get service ai-gateway -n ai-platform
```

### 2. RAG Pipeline

```bash
# Deploy RAG workers
kubectl apply -f kubernetes/rag-workers.yaml

# Scale workers
kubectl scale deployment rag-workers --replicas=5 -n ai-platform
```

### 3. Vector Database

```bash
# Deploy vector database
kubectl apply -f kubernetes/vector-db.yaml

# Initialize index
python scripts/init_vector_db.py
```

### 4. Monitoring Stack

```bash
# Deploy Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n ai-platform

# Deploy Grafana dashboards
kubectl apply -f kubernetes/grafana-dashboards.yaml
```

## Health Checks

### Application Health

```bash
# Check API health
curl http://ai-platform-api:8000/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2026-07-31T10:00:00Z",
  "version": "1.0.0"
}
```

### Component Health

```bash
# Check all components
curl http://ai-platform-api:8000/health/detailed

# Expected response
{
  "status": "healthy",
  "components": {
    "database": {"healthy": true},
    "redis": {"healthy": true},
    "vector_db": {"healthy": true},
    "kafka": {"healthy": true}
  }
}
```

## Scaling

### Horizontal Scaling

```bash
# Scale API Gateway
kubectl scale deployment ai-gateway --replicas=5 -n ai-platform

# Scale RAG workers
kubectl scale deployment rag-workers --replicas=10 -n ai-platform

# Auto-scaling configuration
kubectl apply -f kubernetes/hpa.yaml
```

### Performance Tuning

**API Gateway**
- Workers: 4 per pod
- Max connections: 1000
- Keep-alive: 60s

**RAG Workers**
- Workers: 2 per pod
- Batch size: 10 documents
- Embedding timeout: 30s

## Monitoring

### Prometheus Metrics

```yaml
# Scrape configuration
scrape_configs:
  - job_name: 'ai-platform'
    static_configs:
      - targets: ['ai-gateway:8000']
    metrics_path: '/metrics'
```

### Key Metrics

- Request latency (p50, p95, p99)
- Error rate
- Token usage
- Retrieval accuracy
- Queue depth

### Alerts

```yaml
groups:
  - name: ai_platform_alerts
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, request_latency) > 1000
        for: 5m
        annotations:
          summary: "High latency detected"
          
      - alert: HighErrorRate
        expr: rate(errors[5m]) > 0.05
        for: 2m
        annotations:
          summary: "High error rate"
```

## Backup & Recovery

### Database Backup

```bash
# Backup PostgreSQL
pg_dump -h postgres-host -U user ai_platform > backup.sql

# Restore
psql -h postgres-host -U user ai_platform < backup.sql
```

### Vector Database Backup

```bash
# Pinecone (managed)
# Export vectors to S3
python scripts/backup_vectors.py

# Restore
python scripts/restore_vectors.py
```

## Security

### TLS Configuration

```yaml
# Kubernetes secret
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-platform-policy
spec:
  podSelector:
    matchLabels:
      app: ai-platform
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
          port: 8000
```

## Troubleshooting

### Common Issues

**High Memory Usage**
```bash
# Check memory usage
kubectl top pods -n ai-platform

# Increase memory limits
kubectl patch deployment ai-gateway -n ai-platform \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"ai-gateway","resources":{"limits":{"memory":"16Gi"}}}]}}}}'
```

**Slow Vector Search**
```bash
# Check vector DB metrics
curl http://vector-db:8080/metrics

# Scale vector DB
kubectl scale deployment vector-db --replicas=3 -n ai-platform
```

## Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/ai-gateway -n ai-platform

# Check rollout status
kubectl rollout status deployment/ai-gateway -n ai-platform
```

## Maintenance

### Updates

```bash
# Rolling update
kubectl set image deployment/ai-gateway \
  ai-gateway=ai-platform:1.1.0 \
  -n ai-platform

# Monitor rollout
kubectl rollout status deployment/ai-gateway -n ai-platform
```

### Logs

```bash
# View logs
kubectl logs -f deployment/ai-gateway -n ai-platform

# View logs with timestamps
kubectl logs -f deployment/ai-gateway -n ai-platform --timestamps
```

## Performance Benchmarks

### Expected Performance

| Metric | Target | Actual |
|--------|--------|--------|
| API Latency (p95) | <500ms | ___ |
| RAG Query Latency | <2s | ___ |
| Embedding Generation | <100ms | ___ |
| Vector Search | <50ms | ___ |
| Throughput | >100 RPS | ___ |

### Load Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

## Disaster Recovery

### Backup Strategy

- **Database**: Daily automated backups
- **Vectors**: Weekly exports to S3
- **Configuration**: Git version control
- **Models**: MLflow registry

### Recovery Time Objectives

- **RTO**: 1 hour
- **RPO**: 15 minutes

## Support

For deployment issues:
- Check logs: `kubectl logs -f deployment/ai-gateway -n ai-platform`
- Review metrics: Grafana dashboard
- Contact: ai-platform@example.com