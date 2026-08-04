# Developer Experience Guide

## Overview

This guide outlines the developer experience (DX) principles, tools, and workflows for the Enterprise Platform Engineering IDP. Our goal is to enable developers to be productive from day one with minimal friction.

## Core DX Principles

### 1. Self-Service First

Developers should never need to wait for the platform team to provision resources or deploy applications.

**Target Metrics**:
- 80%+ self-service adoption
- < 30 minutes time to first deployment
- < 5% require platform team support

### 2. Golden Paths

Provide pre-approved, production-ready templates for common use cases.

**Benefits**:
- Best practices built-in
- Security and compliance by default
- Faster development cycles
- Reduced cognitive load

### 3. Low Friction

Minimize the number of steps and decisions required.

**Examples**:
- Single command deployments
- Sensible defaults
- Auto-completion in CLI
- Interactive wizards

### 4. Clear Documentation

Every feature, template, and API should be well-documented.

**Requirements**:
- Getting started guide
- API reference
- Video tutorials
- Example code
- Troubleshooting guides

### 5. Fast Feedback

Provide immediate feedback on actions.

**Examples**:
- Real-time validation
- Instant status updates
- Quick error messages
- Live logs streaming

## Platform CLI

### Installation

```bash
# Install via pip
pip install platform-cli

# Or via homebrew (macOS)
brew install platform/tap/platform-cli

# Verify installation
platform --version
```

### Authentication

```bash
# Login with SSO
platform login

# Login with username/password
platform login --username user@example.com

# Login with API token
platform login --token your-api-token

# Check current user
platform whoami

# Logout
platform logout
```

### Template Management

```bash
# List all templates
platform templates list

# Filter by category
platform templates list --category data-platform

# Search templates
platform templates search "data lake"

# Get template details
platform templates get data-lake-medallion

# View template schema
platform templates schema data-lake-medallion

# Validate template variables
platform templates validate data-lake-medallion --var project_name=myproject
```

### Provisioning

```bash
# Provision from template
platform provision \
  --template data-lake-medallion \
  --var project_name=my-data-lake \
  --var environment=dev \
  --team data-team

# Provision with file
platform provision \
  --template data-lake-medallion \
  --var-file vars.yaml \
  --team data-team

# Example vars.yaml
cat > vars.yaml <<EOF
project_name: my-data-lake
environment: dev
storage_tier: standard
enable_monitoring: true
EOF

# Check provisioning status
platform status <request-id>

# Watch provisioning progress
platform status <request-id> --watch

# View provisioning logs
platform logs <request-id>

# Stream logs in real-time
platform logs <request-id> --follow

# Cancel provisioning
platform cancel <request-id>
```

### Resource Management

```bash
# List all resources
platform resources list

# Filter by team
platform resources list --team data-team

# Filter by environment
platform resources list --environment dev

# Get resource details
platform resources get <resource-id>

# Get resource logs
platform resources logs <resource-id>

# Delete resource
platform resources delete <resource-id> --confirm

# Stop resource
platform resources stop <resource-id>

# Start resource
platform resources start <resource-id>
```

### Cost Management

```bash
# View team costs
platform costs --team data-team

# View project costs
platform costs --project my-data-lake

# Cost breakdown by resource type
platform costs breakdown --team data-team

# Cost trends
platform costs trends --last 30d

# Set budget alert
platform budgets set --team data-team --amount 1000 --threshold 80

# View budgets
platform budgets list
```

### Configuration

```bash
# Set default environment
platform config set default-environment dev

# Set default team
platform config set default-team data-team

# Set API endpoint
platform config set endpoint https://platform.example.com

# View configuration
platform config list

# Reset configuration
platform config reset
```

### Help & Support

```bash
# General help
platform --help

# Command-specific help
platform provision --help

# Show examples
platform examples provision

# Open documentation
platform docs

# Report issue
platform report-issue

# Check for updates
platform update --check
```

## Python SDK

### Installation

```bash
pip install platform-sdk
```

### Basic Usage

```python
from platform_sdk import PlatformClient
from platform_sdk.models import ProvisioningRequest

# Initialize client
client = PlatformClient(
    endpoint="https://platform.example.com",
    token="your-jwt-token"  # Or use OAuth
)

# List available templates
templates = client.templates.list()
for template in templates:
    print(f"{template.name}: {template.description}")

# Filter templates
data_templates = client.templates.list(category="data-platform")

# Get template details
template = client.templates.get("data-lake-medallion")
print(f"Variables: {template.variables}")

# Provision resources
request = client.provisioning.create(
    template_id="data-lake-medallion",
    variables={
        "project_name": "my-data-lake",
        "environment": "dev",
        "storage_tier": "standard"
    },
    team="data-team",
    environment="dev"
)

print(f"Request ID: {request.id}")
print(f"Status: {request.status}")

# Wait for completion
import asyncio

async def wait_for_provisioning(request_id):
    while True:
        status = client.provisioning.get(request_id)
        print(f"Status: {status.status}")

        if status.status in ["completed", "failed"]:
            return status

        await asyncio.sleep(5)

# Or use the waiter helper
status = client.provisioning.wait(request.id, timeout=600)

if status.status == "completed":
    print(f"Resources provisioned successfully!")
    print(f"Outputs: {status.outputs}")
else:
    print(f"Provisioning failed: {status.error}")
```

### Advanced Usage

```python
# Async client
from platform_sdk import AsyncPlatformClient

async def provision_multiple():
    async with AsyncPlatformClient(endpoint="...", token="...") as client:
        # Provision multiple resources in parallel
        requests = await asyncio.gather(
            client.provisioning.create(
                template_id="data-lake",
                variables={"project_name": "project1"},
                team="team1"
            ),
            client.provisioning.create(
                template_id="kafka-cluster",
                variables={"name": "kafka1"},
                team="team1"
            )
        )
        return requests

# Event streaming
def watch_provisioning(request_id):
    for event in client.provisioning.events(request_id):
        print(f"[{event.timestamp}] {event.level}: {event.message}")

# Batch operations
def batch_delete(resource_ids):
    for resource_id in resource_ids:
        client.resources.delete(resource_id, confirm=True)

# Context manager for automatic cleanup
with client.provisioning.batch() as batch:
    batch.create(template_id="template1", variables={...})
    batch.create(template_id="template2", variables={...})
    results = batch.execute()
```

### Error Handling

```python
from platform_sdk.exceptions import (
    ValidationError,
    PolicyViolationError,
    ApprovalRequiredError,
    ProvisioningError
)

try:
    request = client.provisioning.create(...)
except ValidationError as e:
    print(f"Invalid request: {e.errors}")
except PolicyViolationError as e:
    print(f"Policy violations: {e.violations}")
except ApprovalRequiredError as e:
    print(f"Approval required: {e.approval_url}")
except ProvisioningError as e:
    print(f"Provisioning failed: {e.message}")
```

## Developer Portal

### Getting Started

1. **Sign In**
   - Use SSO (Azure AD, Google, GitHub)
   - First time? Complete profile setup
   - Join or create a team

2. **Dashboard Overview**
   ```
   ┌─────────────────────────────────────────┐
   │ My Resources          Cost: $234/month  │
   ├─────────────────────────────────────────┤
   │ Recent Requests                         │
   │ • data-lake-dev    ✓ Completed          │
   │ • kafka-prod       ⟳ Provisioning      │
   │ • ml-training      ⏸ Pending Approval  │
   └─────────────────────────────────────────┘
   ```

3. **Browse Templates**
   - Search or filter templates
   - View documentation
   - See examples
   - Check requirements

4. **Provision Resources**
   - Select template
   - Fill in variables
   - Review cost estimate
   - Submit request

### Template Wizard

The provisioning wizard guides you through the process:

```
Step 1: Select Template
  └─ Search or browse
  └─ View details
  └─ Check requirements

Step 2: Configure
  └─ Fill required variables
  └─ Review optional settings
  └─ See cost estimate

Step 3: Review & Submit
  └─ Validate configuration
  └─ Check policy compliance
  └─ Add comments (if needed)
  └─ Submit request

Step 4: Track Progress
  └─ Real-time status updates
  └─ Live logs
  └─ Approval workflow (if needed)

Step 5: Access Resources
  └─ Connection details
  └─ Documentation
  └─ Quick start guides
```

### Resource Dashboard

View and manage your resources:

```
┌──────────────────────────────────────────┐
│ My Resources                             │
├──────────────────────────────────────────┤
│ Data Lakes (3)                           │
│  • my-data-lake-dev    Running           │
│  • my-data-lake-staging Running          │
│  • analytics-lake-prod Running           │
│                                          │
│ Kafka Clusters (2)                       │
│  • events-dev          Running           │
│  • events-prod         Running           │
│                                          │
│ ML Projects (1)                          │
│  • churn-prediction    Training          │
└──────────────────────────────────────────┘
```

### Cost Dashboard

Monitor your spending:

```
┌──────────────────────────────────────────┐
│ Team: Data Team  |  Month: January 2026  │
├──────────────────────────────────────────┤
│ Total: $3,456 / Budget: $5,000 (69%)    │
│                                          │
│ Breakdown:                               │
│ • Data Lakes        $1,234 (36%)        │
│ • Kafka Clusters    $876   (25%)        │
│ • ML Infrastructure $1,234 (36%)        │
│ • Other             $112   (3%)         │
│                                          │
│ Top Projects:                            │
│ 1. analytics-lake    $1,456             │
│ 2. ml-platform       $1,234             │
│ 3. streaming-pipeline $876              │
└──────────────────────────────────────────┘
```

## API Reference

### Authentication

```python
# Get JWT token
POST /api/v1/auth/login
{
  "username": "user@example.com",
  "password": "password"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 1800
}
```

### Templates

```python
# List templates
GET /api/v1/templates?category=data-platform

Response:
{
  "templates": [
    {
      "id": "template-123",
      "name": "Data Lake Medallion",
      "category": "data-platform",
      "version": "1.2.0",
      "description": "...",
      "variables": [...]
    }
  ],
  "total": 15
}

# Provision from template
POST /api/v1/templates/{template_id}/provision
Headers: { "Authorization": "Bearer <token>" }

Request:
{
  "variables": {
    "project_name": "my-project",
    "environment": "dev"
  },
  "team": "data-team",
  "environment": "dev"
}

Response:
{
  "request_id": "prov-123",
  "status": "pending",
  "estimated_time": "5m",
  "approval_url": null
}
```

## Common Workflows

### Workflow 1: Create Data Lake

```bash
# 1. Find template
platform templates search "data lake"

# 2. Check requirements
platform templates get data-lake-medallion

# 3. Provision
platform provision \
  --template data-lake-medallion \
  --var project_name=analytics-lake \
  --var environment=prod \
  --team data-team

# 4. Wait for completion
platform status <request-id> --watch

# 5. Get connection details
platform resources get analytics-lake-prod

# 6. Connect and start using
# Connection string provided in output
```

### Workflow 2: Deploy Kafka Topic

```bash
# 1. List available templates
platform templates list --category streaming

# 2. Provision Kafka topic
platform provision \
  --template kafka-topic \
  --var topic_name=user-events \
  --var partitions=12 \
  --var replication_factor=3 \
  --team streaming-team

# 3. Get connection details
platform resources get user-events

# 4. Produce/consume messages
# Bootstrap servers and credentials provided
```

### Workflow 3: Train ML Model

```bash
# 1. Provision ML project
platform provision \
  --template ml-training-pipeline \
  --var project_name=churn-prediction \
  --var environment=dev \
  --team ml-team

# 2. Access MLflow
platform resources get churn-prediction-mlflow

# 3. Start training
python train.py --tracking-uri <mlflow-uri>

# 4. Deploy model
platform provision \
  --template model-serving \
  --var model_name=churn-predictor \
  --var model_version=v1 \
  --team ml-team
```

## Troubleshooting

### Common Issues

**Issue**: Provisioning stuck in "validating" state

**Solution**:
```bash
# Check logs
platform logs <request-id>

# Common causes:
# - Invalid variables
# - Policy violation
# - Approval pending

# Cancel and retry
platform cancel <request-id>
platform provision ...
```

**Issue**: Template validation fails

**Solution**:
```bash
# Validate variables
platform templates validate <template-id> --var-file vars.yaml

# Common issues:
# - Missing required variables
# - Invalid pattern match
# - Wrong data type
```

**Issue**: Permission denied

**Solution**:
```bash
# Check team membership
platform teams list

# Request access
platform teams request-access <team-name>

# Check your permissions
platform auth permissions
```

### Getting Help

```bash
# View command help
platform --help
platform <command> --help

# Show examples
platform examples <command>

# Interactive mode
platform interactive

# Contact support
platform support
```

## Best Practices

### 1. Use Golden Paths

Always start with golden path templates. They provide:
- Best practices
- Security defaults
- Cost optimization
- Monitoring setup

### 2. Tag Resources

Always include meaningful tags:
```bash
platform provision \
  --template my-template \
  --var project_name=myproject \
  --var environment=prod \
  --var owner=john.doe@example.com \
  --var cost_center=data-engineering
```

### 3. Monitor Costs

Check costs regularly:
```bash
# Daily
platform costs --team my-team --last 1d

# Weekly report
platform costs report --team my-team --period week

# Set alerts
platform budgets set --team my-team --amount 1000
```

### 4. Clean Up Resources

Delete unused resources:
```bash
# List old resources
platform resources list --older-than 30d

# Batch delete
platform resources delete <resource-id-1> <resource-id-2>

# Auto-cleanup (set on provision)
platform provision ... --auto-cleanup 7d
```

### 5. Use Environments

Follow environment naming:
- `dev` - Development, can be destroyed
- `staging` - Pre-production testing
- `prod` - Production, requires approval

## Feedback & Contributions

### Provide Feedback

```bash
# Submit feedback
platform feedback

# Report bugs
platform report-bug

# Request features
platform request-feature
```

### Contribute Templates

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Metrics & Analytics

### Your Personal Metrics

```bash
# View your activity
platform analytics my-activity --last 30d

# Your deployments
platform analytics my-deployments --last 30d

# Your costs
platform analytics my-costs --last 30d
```

### Team Metrics

```bash
# Team activity
platform analytics team-activity --team data-team

# Team velocity
platform analytics team-velocity --team data-team

# Team costs
platform analytics team-costs --team data-team
```

## Resources

- [Platform Documentation](https://docs.platform.example.com)
- [API Reference](https://api.platform.example.com/docs)
- [Video Tutorials](https://platform.example.com/tutorials)
- [Community Forum](https://community.platform.example.com)
- [Support](mailto:platform-support@example.com)