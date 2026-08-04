# Internal Developer Platform (IDP) Guide

## What is an Internal Developer Platform?

An Internal Developer Platform (IDP) is a self-service platform that enables development teams to deploy and manage applications and infrastructure without deep expertise in the underlying technologies. It abstracts away complexity while maintaining governance and security.

### Key Characteristics

1. **Self-Service** - Developers can provision resources independently
2. **Golden Paths** - Pre-approved, opinionated templates
3. **Low Friction** - Streamlined workflows with minimal steps
4. **Governed** - Policies and guardrails built-in
5. **Observable** - Full visibility into operations

## IDP vs. DevOps

| Aspect | DevOps | Platform Engineering (IDP) |
|--------|---------|---------------------------|
| Focus | Culture, practices, tools | Product, self-service, developer experience |
| Audience | Everyone | Developers |
| Goal | CI/CD, automation | Reduce cognitive load, enable speed |
| Approach | Teach tools | Provide paved roads |
| Metric | Deployment frequency | Developer satisfaction, time-to-value |

## Building an IDP for Data & AI Teams

### Who Are Our Users?

1. **Data Engineers** - Need data lakes, warehouses, streaming
2. **Analytics Engineers** - Need transformation pipelines, marts
3. **ML Engineers** - Need training pipelines, feature stores, model serving
4. **AI Engineers** - Need agent platforms, RAG systems, LLM deployments
5. **Platform Engineers** - Need infrastructure automation, monitoring

### Platform Maturity Model

```
Level 1: Ad Hoc
├── Manual deployments
├── No standardization
└── Hero culture

Level 2: Repeatable
├── Basic CI/CD
├── Some automation
└── Documentation

Level 3: Defined
├── Standardized processes
├── Self-service capabilities
└── Golden paths

Level 4: Measured
├── Metrics and monitoring
├── Developer analytics
└── Continuous improvement

Level 5: Optimizing
├── Automated optimization
├── Predictive analytics
└── Zero-touch operations
```

## IDP Components

### 1. Developer Portal

The primary interface for developers to interact with the platform.

**Core Features**:
- Service catalog with search
- Template browser
- Provisioning wizard
- Status dashboard
- Documentation hub
- Support and feedback

**User Journey**:
```
Login
  ↓
Browse Services
  ↓
Select Template
  ↓
Configure Variables
  ↓
Policy Validation
  ↓
Submit Request
  ↓
Track Progress
  ↓
Access Resources
  ↓
Monitor & Operate
```

### 2. Service Catalog

A registry of all services, templates, and capabilities offered by the platform.

**Information Architecture**:
```
Platform Services
├── Data Platform
│   ├── Data Lakes (ADLS, S3, GCS)
│   ├── Warehouses (Snowflake, BigQuery, Synapse)
│   ├── Streaming (Kafka, Event Hub, Pub/Sub)
│   └── Orchestration (Airflow, Prefect, Dagster)
├── AI Platform
│   ├── MLflow (experiments, models)
│   ├── Feature Store (Feast, Tecton)
│   ├── Model Serving (KServe, Seldon)
│   └── Vector DB (Pinecone, Weaviate)
└── Infrastructure
    ├── Kubernetes Namespaces
    ├── Databases (PostgreSQL, MySQL)
    ├── Caches (Redis, Memcached)
    └── Secrets (Vault, Key Vault)
```

### 3. Golden Paths

Pre-approved, production-ready deployment patterns.

**Data Lake Golden Path**:
```
Template: data-lake-medallion
├── Storage: ADLS Gen2 / S3 / GCS
├── Formats: Delta Lake / Iceberg
├── Layers: Bronze, Silver, Gold
├── Governance: Unity Catalog / Purview
├── Monitoring: Datadog / Azure Monitor
└── CI/CD: GitHub Actions
```

**Streaming Pipeline Golden Path**:
```
Template: kafka-streaming
├── Kafka Cluster (Confluent / MSK / Event Hub)
├── Schema Registry
├── Streaming Job (Spark Structured Streaming)
├── Checkpointing (S3 / ADLS)
├── Monitoring (Prometheus + Grafana)
└── Alerting (PagerDuty / Opsgenie)
```

**ML Pipeline Golden Path**:
```
Template: ml-training-pipeline
├── MLflow Tracking Server
├── Feature Store (Feast)
├── Training Job (Databricks / SageMaker)
├── Model Registry
├── Deployment (KServe)
└── Monitoring (Evidently AI)
```

### 4. Template System

Templates encode best practices and organizational standards.

**Template Anatomy**:
```yaml
# template.yaml
apiVersion: platform/v1
kind: Template
metadata:
  name: data-lake-medallion
  version: 1.2.0
  category: data-platform
  description: Production-ready data lake with medallion architecture

variables:
  - name: project_name
    type: string
    required: true
    pattern: "^[a-z0-9-]{3,30}$"
    description: "Unique project identifier"

  - name: storage_account
    type: string
    required: true
    description: "Storage account name"

  - name: environment
    type: string
    required: true
    enum: [dev, staging, prod]
    default: dev

  - name: retention_days
    type: number
    required: false
    default: 30
    validation:
      minimum: 1
      maximum: 365

  - name: enable_encryption
    type: boolean
    required: false
    default: true

validation:
  policy: data-lake-policy
  required_approvers: [data-team-lead]

resources:
  - storage: bronze-layer
  - storage: silver-layer
  - storage: gold-layer
  - pipeline: ingestion-job
  - monitoring: dashboards

outputs:
  - bronze_path: "abfss://bronze@{storage_account}.dfs.core.windows.net/"
  - silver_path: "abfss://silver@{storage_account}.dfs.core.windows.net/"
  - gold_path: "abfss://gold@{storage_account}.dfs.core.windows.net/"
```

### 5. Provisioning Engine

Orchestrates the end-to-end provisioning workflow.

**Provisioning Pipeline**:
```python
class ProvisioningPipeline:
    async def provision(self, request):
        # Step 1: Validate request
        validation = await self.validate(request)
        if not validation.valid:
            raise ValidationError(validation.errors)

        # Step 2: Check policies
        policy_result = await self.policy_engine.evaluate(request)
        if policy_result.deny:
            raise PolicyViolationError(policy_result.violations)

        # Step 3: Approval workflow
        if policy_result.requires_approval:
            approval_id = await self.approval_service.create(request)
            return ApprovalPending(approval_id)

        # Step 4: Render template
        config = await self.template_engine.render(
            request.template_id,
            request.variables
        )

        # Step 5: Provision infrastructure
        infra = await self.terraform.apply(config.infrastructure)

        # Step 6: Deploy applications
        apps = await self.kubernetes.deploy(config.manifests)

        # Step 7: Setup monitoring
        await self.monitoring.setup(request.name)

        # Step 8: Register in catalog
        await self.catalog.register(request, infra, apps)

        # Step 9: Send notifications
        await self.notifications.send(request.requested_by, "complete")

        return ProvisioningComplete(infra, apps)
```

### 6. Governance Engine

Enforces organizational policies and compliance requirements.

**Policy Types**:

**Security**:
```rego
# Encryption at rest
deny[msg] {
  input.resource.type == "storage_account"
  not input.resource.properties.encryption
  msg := "Storage accounts must have encryption enabled"
}

# No public access
deny[msg] {
  input.resource.type == "storage_account"
  input.resource.properties.public_access == "enabled"
  msg := "Storage accounts cannot have public access"
}
```

**Cost**:
```rego
# Maximum VM size
deny[msg] {
  input.resource.type == "virtual_machine"
  input.resource.properties.vm_size == "Standard_E64s_v3"
  msg := "VM size exceeds maximum allowed (Standard_E32s_v3)"
}

# Dev environment auto-shutdown
deny[msg] {
  input.resource.type == "virtual_machine"
  input.resource.tags.environment == "dev"
  not input.resource.properties.auto_shutdown
  msg := "Dev VMs must have auto-shutdown enabled"
}
```

**Compliance**:
```rego
# Data residency
deny[msg] {
  input.resource.type == "storage_account"
  input.resource.properties.location == "eastus"
  input.resource.tags.data_classification == "PII"
  msg := "PII data must be stored in compliant regions"
}
```

### 7. Approval Workflows

Human-in-the-loop approval for sensitive operations.

**Approval Matrix**:
```
Resource Type              | Environment | Requires Approval
---------------------------|-------------|------------------
Data Lake                  | dev         | No
Data Lake                  | prod        | Yes (Data Team Lead)
Kafka Cluster              | dev         | No
Kafka Cluster              | prod        | Yes (Platform Team)
ML Model Deployment        | any         | Yes (ML Lead)
Infrastructure Changes     | prod        | Yes (Platform + SRE)
Cost > $1000/month         | any         | Yes (Finance)
```

**Workflow States**:
```
CREATED → PENDING_APPROVAL → APPROVED → EXECUTING → COMPLETED
                ↓                        ↓
             REJECTED                 FAILED
```

## Platform APIs

### REST API Design

**Authentication Endpoints**:
```yaml
POST /api/v1/auth/login
  Request: { username, password }
  Response: { access_token, refresh_token, expires_in }

POST /api/v1/auth/refresh
  Request: { refresh_token }
  Response: { access_token, refresh_token }

POST /api/v1/auth/logout
  Request: { refresh_token }
  Response: { success }
```

**Service Catalog Endpoints**:
```yaml
GET /api/v1/services
  Query: category, team, search, limit, offset
  Response: { services: [...], total: 100 }

GET /api/v1/services/{id}
  Response: { service: {...} }

POST /api/v1/services
  Request: { name, category, description, ... }
  Response: { service: {...} }
```

**Template Endpoints**:
```yaml
GET /api/v1/templates
  Query: category, search, limit
  Response: { templates: [...], total: 50 }

GET /api/v1/templates/{id}
  Response: { template: {...} }

POST /api/v1/templates/{id}/provision
  Request: { variables, environment, team }
  Response: { request_id, status, approval_url? }
```

**Provisioning Endpoints**:
```yaml
GET /api/v1/provisioning/requests
  Query: status, team, environment, limit
  Response: { requests: [...], total: 25 }

GET /api/v1/provisioning/requests/{id}
  Response: { request: {...} }

POST /api/v1/provisioning/requests/{id}/approve
  Request: { approver, comments }
  Response: { request: {...} }

GET /api/v1/provisioning/requests/{id}/logs
  Response: { logs: [...] }
```

## Platform SDK

### Python SDK

**Installation**:
```bash
pip install platform-sdk
```

**Usage**:
```python
from platform_sdk import PlatformClient

# Initialize client
client = PlatformClient(
    endpoint="https://platform.example.com",
    token="your-jwt-token"
)

# List templates
templates = client.templates.list(category="data-platform")

# Provision resources
request = client.provisioning.create(
    template_id="data-lake-medallion",
    variables={
        "project_name": "my-data-lake",
        "storage_account": "mydatalake",
        "environment": "dev"
    },
    team="data-team"
)

# Check status
status = client.provisioning.get(request.id)
print(f"Status: {status.state}")

# List provisioned resources
resources = client.catalog.list(team="data-team")
for resource in resources:
    print(f"{resource.name}: {resource.status}")
```

### CLI Tool

**Installation**:
```bash
pip install platform-cli
```

**Usage**:
```bash
# Login
platform login --endpoint https://platform.example.com

# List templates
platform templates list --category data-platform

# Provision data lake
platform provision \
  --template data-lake-medallion \
  --var project_name=my-data-lake \
  --var storage_account=mydatalake \
  --var environment=dev \
  --team data-team

# Check status
platform status <request-id>

# View logs
platform logs <request-id> --tail 100

# List resources
platform resources list --team data-team

# Get resource details
platform resources get <resource-id>

# Delete resource
platform resources delete <resource-id> --confirm
```

## Developer Experience

### Time to First Deployment

**Goal**: < 30 minutes from signup to first deployment

**Steps**:
1. Sign up with SSO (5 min)
2. Join a team (2 min)
3. Browse golden paths (3 min)
4. Select template (2 min)
5. Configure and submit (5 min)
6. Approval (if needed) (10 min)
7. Automatic provisioning (5 min)

**Total**: ~32 minutes

### Self-Service Adoption

**Target Metrics**:
- 80% of deployments via self-service
- 90% developer satisfaction
- < 5% require platform team support
- 50% reduction in time-to-market

### Developer Dashboard

**Metrics Displayed**:
- My active resources
- Recent provisioning requests
- Cost per team/project
- Team activity
- Documentation links
- Support channels

## Golden Path Implementation

### Creating a Golden Path

**1. Identify Common Pattern**:
- Talk to developers
- Analyze existing deployments
- Find repetitive tasks
- Identify pain points

**2. Design Template**:
- Define variables
- Set validation rules
- Create infrastructure code
- Add default values

**3. Add Governance**:
- Define policies
- Set approval requirements
- Configure cost limits
- Add monitoring

**4. Document**:
- Write README
- Create examples
- Record video tutorial
- Add to service catalog

**5. Test**:
- Deploy to dev
- Test all variations
- Verify policies
- Validate monitoring

**6. Publish**:
- Add to portal
- Announce to team
- Gather feedback
- Iterate

### Example: Data Lake Template

```python
# Template definition
TEMPLATE = {
    "name": "data-lake-medallion",
    "version": "1.0.0",
    "description": "Data lake with bronze, silver, gold layers",
    "category": "data-platform",

    "variables": {
        "project_name": {
            "type": "string",
            "required": True,
            "pattern": "^[a-z0-9-]{3,30}$",
            "description": "Project name"
        },
        "environment": {
            "type": "string",
            "required": True,
            "enum": ["dev", "staging", "prod"],
            "default": "dev"
        },
        "storage_tier": {
            "type": "string",
            "required": False,
            "enum": ["standard", "premium"],
            "default": "standard"
        }
    },

    "resources": {
        "storage_bronze": {
            "type": "storage_account",
            "source": "terraform/modules/storage-account"
        },
        "storage_silver": {
            "type": "storage_account",
            "source": "terraform/modules/storage-account"
        },
        "storage_gold": {
            "type": "storage_account",
            "source": "terraform/modules/storage-account"
        },
        "bronze_ingestion": {
            "type": "airflow_dag",
            "source": "dags/bronze_ingestion"
        }
    },

    "policies": [
        "storage-encryption-required",
        "no-public-access",
        "cost-limit-1000"
    ],

    "approval": {
        "prod": ["data-team-lead", "platform-lead"],
        "staging": ["data-team-lead"]
    }
}
```

## Platform Best Practices

### Template Design

1. **Opinionated Defaults** - Sensible defaults for 80% use cases
2. **Flexibility** - Allow customization when needed
3. **Documentation** - Clear variable descriptions
4. **Examples** - Real-world usage examples
5. **Testing** - Automated template validation

### Provisioning

1. **Idempotency** - Safe to retry
2. **Rollback** - Easy to undo
3. **Validation** - Check before apply
4. **Progress** - Real-time status updates
5. **Notifications** - Keep users informed

### Governance

1. **Least Privilege** - Minimum permissions
2. **Defense in Depth** - Multiple policy layers
3. **Audit Everything** - Complete audit trail
4. **Policy as Code** - Version controlled
5. **Fast Feedback** - Fail fast, inform early

### Monitoring

1. **Platform Health** - Monitor the platform itself
2. **Resource Metrics** - CPU, memory, storage
3. **Business Metrics** - Adoption, satisfaction
4. **Cost Metrics** - Track spending
5. **Alerting** - Proactive notifications

## Common Pitfalls

### Anti-Patterns

1. **Platform as Jail** - Too restrictive, developers find workarounds
2. **Platform as Wild West** - No standards, chaos
3. **Build Everything** - Platform team builds all solutions
4. **Ignore Feedback** - Don't listen to developers
5. **Over-Engineering** - Build for scale that doesn't exist

### Solutions

1. **Balance** - Provide defaults with escape hatches
2. **Iterate** - Start small, improve based on feedback
3. **Enable** - Give tools, don't build for them
4. **Listen** - Regular surveys, office hours
5. **YAGNI** - You Aren't Gonna Need It

## Measuring Success

### Key Metrics

**Adoption**:
- % deployments via platform
- Active users
- Template usage

**Velocity**:
- Time to provision
- Time to deploy
- Lead time

**Quality**:
- Provisioning success rate
- Incident rate
- Security findings

**Cost**:
- Cost per developer
- Resource utilization
- Waste reduction

**Satisfaction**:
- NPS score
- Support tickets
- Feedback sentiment

## Conclusion

Building an IDP is a journey, not a destination. Start with the most critical pain points, deliver value quickly, and iterate based on developer feedback. The goal is to enable developers to focus on business logic while the platform handles infrastructure complexity.

Remember: **Platform as a Product**, not a project.