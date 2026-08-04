# Enterprise Data Fabric - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Enterprise Data Fabric platform in production environments.

## Architecture

The Enterprise Data Fabric platform consists of:

- **Metadata Layer**: Central metadata repository with active metadata management
- **Knowledge Graph**: Neo4j-based graph for relationship mapping
- **Catalog Service**: Enterprise data catalog with search capabilities
- **Policy Engine**: Automated governance and compliance
- **Connectors**: Multi-platform metadata harvesting
- **API Layer**: RESTful APIs for integration
- **Monitoring**: Health checks, metrics, and SLA tracking

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32+ GB |
| Storage | 100 GB SSD | 500+ GB SSD |

### Software Requirements

- Python 3.13+
- Docker & Docker Compose
- Kubernetes (for production)
- Neo4j 5.x
- PostgreSQL 14+ (optional, for metadata persistence)
- Redis (for caching)

## Deployment Options

### Option 1: Docker Compose (Development)

```bash
# Clone repository
git clone <repository-url>
cd production-data-engineering-projects/projects/22_enterprise_data_fabric

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
kubectl apply -f infrastructure/kubernetes/deployment.yaml
kubectl apply -f infrastructure/kubernetes/service.yaml
kubectl apply -f infrastructure/kubernetes/ingress.yaml
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

Create a `.env` file in the project root:

```bash
# Application
APP_NAME=data-fabric
APP_ENV=production
LOG_LEVEL=INFO

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=data_fabric
POSTGRES_USER=data_fabric
POSTGRES_PASSWORD=<secure-password>

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure-password>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<secure-password>

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Connectors
SNOWFLAKE_ACCOUNT=<account>
SNOWFLAKE_USER=<user>
SNOWFLAKE_PASSWORD=<password>

DATABRICKS_WORKSPACE_URL=<url>
DATABRICKS_TOKEN=<token>

KAFKA_BOOTSTRAP_SERVERS=<servers>

AIRFLOW_API_URL=<url>
AIRFLOW_USERNAME=<user>
AIRFLOW_PASSWORD=<password>

AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>

AZURE_SUBSCRIPTION_ID=<id>
AZURE_TENANT_ID=<tenant>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<secret>
```

### Platform Configuration

Create `configs/platform.yaml`:

```yaml
platform:
  name: "Enterprise Data Fabric"
  version: "1.0.0"
  environment: production

metadata:
  repository:
    type: postgresql
    pool_size: 20
    max_overflow: 10
  
  harvester:
    batch_size: 100
    max_workers: 10
    harvest_interval: 3600  # seconds

catalog:
  search:
    index_refresh_interval: 300
    max_results: 1000
  
  lineage:
    max_depth: 10
    cache_ttl: 3600

knowledge_graph:
  neo4j:
    pool_size: 50
    max_retries: 3
    timeout: 30

policies:
  evaluation_timeout: 60
  batch_size: 100
  violation_retention_days: 90

apis:
  rate_limit: 1000
  rate_window: 3600
  cors_origins:
    - https://data-fabric.example.com
```

## Installation

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -r requirements.txt
pip install -e .
```

### 2. Initialize Database

```bash
# Run database migrations
alembic upgrade head

# Seed initial data
python scripts/seed_initial_data.py
```

### 3. Initialize Knowledge Graph

```bash
# Create Neo4j constraints and indexes
python scripts/init_knowledge_graph.py
```

### 4. Start Services

```bash
# Start API server
uvicorn apis.main:create_app --host 0.0.0.0 --port 8000 --workers 4

# Start scheduler (in production, use systemd or Kubernetes)
python -m platform.automation.scheduler
```

## Docker Deployment

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://data_fabric:password@postgres:5432/data_fabric
      - REDIS_URL=redis://redis:6379
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - postgres
      - redis
      - neo4j
    volumes:
      - ./configs:/app/configs
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=data_fabric
      - POSTGRES_USER=data_fabric
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  neo4j:
    image: neo4j:5
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j_data:/data
    ports:
      - "7474:7474"
      - "7687:7687"
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  neo4j_data:
```

### Build and Start

```bash
docker-compose up -d --build

# Check logs
docker-compose logs -f api

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
  name: data-fabric
  labels:
    name: data-fabric
```

### Deployment

```yaml
# infrastructure/kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-fabric-api
  namespace: data-fabric
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-fabric-api
  template:
    metadata:
      labels:
        app: data-fabric-api
    spec:
      containers:
      - name: api
        image: data-fabric:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: data-fabric-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: data-fabric-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
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
```

### Service

```yaml
# infrastructure/kubernetes/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: data-fabric-api
  namespace: data-fabric
spec:
  selector:
    app: data-fabric-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress

```yaml
# infrastructure/kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: data-fabric-ingress
  namespace: data-fabric
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - data-fabric.example.com
    secretName: data-fabric-tls
  rules:
  - host: data-fabric.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: data-fabric-api
            port:
              number: 80
```

## Production Best Practices

### 1. Security

- Use secrets management (HashiCorp Vault, AWS Secrets Manager)
- Enable TLS/SSL for all connections
- Implement network policies
- Regular security updates
- Audit logging enabled

### 2. High Availability

- Deploy multiple API replicas
- Use load balancers
- Database replication
- Redis cluster for caching
- Neo4j causal cluster

### 3. Monitoring

```bash
# Prometheus metrics endpoint
GET /metrics

# Health check
GET /health

# Detailed health
GET /health/detailed
```

### 4. Backup Strategy

```bash
# PostgreSQL backup
pg_dump -U data_fabric data_fabric > backup.sql

# Neo4j backup
neo4j-admin dump --database=neo4j --to=backup.dump

# Automated backup script
python scripts/backup.py --config configs/backup.yaml
```

## Scaling

### Horizontal Scaling

```bash
# Scale API pods
kubectl scale deployment/data-fabric-api --replicas=10

# Scale workers
kubectl scale deployment/data-fabric-worker --replicas=5
```

### Performance Tuning

```yaml
# configs/performance.yaml
api:
  workers: 8
  max_connections: 1000
  
database:
  pool_size: 50
  max_overflow: 20
  
cache:
  redis_pool_size: 100
  ttl: 3600
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database connectivity
   python scripts/check_database.py
   
   # Verify connection pool
   curl http://localhost:8000/health/detailed
   ```

2. **Neo4j Connection Issues**
   ```bash
   # Test Neo4j connection
   python scripts/check_neo4j.py
   
   # Check Neo4j logs
   docker logs neo4j
   ```

3. **High Memory Usage**
   ```bash
   # Monitor memory
   kubectl top pods
   
   # Adjust worker count
   # Edit deployment and reduce workers
   ```

### Logs

```bash
# Application logs
docker-compose logs -f api

# Kubernetes logs
kubectl logs -f deployment/data-fabric-api -n data-fabric

# Database logs
docker-compose logs -f postgres
```

## Maintenance

### Regular Tasks

1. **Daily**
   - Monitor health dashboard
   - Review policy violations
   - Check harvest status

2. **Weekly**
   - Review discovery report
   - Update connectors
   - Backup verification

3. **Monthly**
   - Security updates
   - Performance tuning
   - Capacity planning

### Updates

```bash
# Rolling update
kubectl set image deployment/data-fabric-api api=data-fabric:v2.0.0

# Verify deployment
kubectl rollout status deployment/data-fabric-api

# Rollback if needed
kubectl rollout undo deployment/data-fabric-api
```

## Support

For issues and questions:
- Documentation: https://data-fabric.example.com/docs
- Issues: https://github.com/org/data-fabric/issues
- Email: support@example.com