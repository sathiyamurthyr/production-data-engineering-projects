# Platform Governance Guide

## Overview

This guide outlines the governance framework for the Enterprise Platform Engineering IDP. Governance ensures that all resources provisioned through the platform comply with organizational policies, security standards, and cost controls.

## Governance Principles

### 1. Policy as Code

All governance policies are defined as code, version-controlled, and automatically enforced.

**Benefits**:
- Consistent enforcement
- Audit trail
- Fast feedback
- Easy updates

### 2. Defense in Depth

Multiple layers of protection:
- Network policies
- RBAC
- Resource quotas
- Policy validation
- Audit logging

### 3. Least Privilege

Minimum permissions required for each role.

### 4. Zero Trust

Never trust, always verify. Every request is validated.

## Policy Framework

### Policy Types

#### Security Policies

**Encryption at Rest**:
```rego
package platform.security

# Require encryption for all storage
deny[msg] {
  input.resource.type in ["storage_account", "database", "disk"]
  not input.resource.properties.encryption_enabled
  msg := sprintf("%s must have encryption at rest enabled", [input.resource.type])
}

# Require TLS for all services
deny[msg] {
  input.resource.type == "load_balancer"
  not input.resource.properties.tls_enabled
  msg := "Load balancers must have TLS enabled"
}
```

**Access Control**:
```rego
# No public access
deny[msg] {
  input.resource.type == "storage_account"
  input.resource.properties.public_access == "enabled"
  msg := "Storage accounts cannot have public access enabled"
}

# Require private endpoints
deny[msg] {
  input.resource.type in ["storage_account", "database"]
  input.environment == "prod"
  not input.resource.properties.private_endpoint
  msg := sprintf("Production %s must use private endpoints", [input.resource.type])
}
```

**Secrets Management**:
```rego
# No hardcoded secrets
deny[msg] {
  input.resource.type == "deployment"
  secret := input.resource.properties.env_vars[_]
  secret.key in ["password", "secret", "api_key", "token"]
  not secret.value.startswith("vault://")
  msg := sprintf("Secret '%s' must be stored in Vault", [secret.key])
}
```

#### Cost Policies

**Budget Limits**:
```rego
package platform.cost

# Maximum monthly cost per team
deny[msg] {
  input.resource.estimated_monthly_cost > 5000
  msg := sprintf("Resource exceeds team budget: $%d > $5000/month", [input.resource.estimated_monthly_cost])
}

# Maximum VM size for non-production
deny[msg] {
  input.resource.type == "virtual_machine"
  input.environment != "prod"
  input.resource.properties.vm_size in ["Standard_E64s_v3", "Standard_E128s_v3"]
  msg := "Non-production environments cannot use large VM sizes"
}
```

**Auto-Shutdown**:
```rego
# Dev VMs must auto-shutdown
deny[msg] {
  input.resource.type == "virtual_machine"
  input.environment == "dev"
  not input.resource.properties.auto_shutdown
  msg := "Development VMs must have auto-shutdown enabled"
}

# Auto-shutdown schedule
deny[msg] {
  input.resource.type == "virtual_machine"
  input.environment == "dev"
  input.resource.properties.auto_shutdown
  input.resource.properties.auto_shutdown_time != "19:00"
  msg := "Dev VMs must shutdown at 19:00"
}
```

#### Compliance Policies

**Data Residency**:
```rego
package platform.compliance

# PII data must be in specific regions
deny[msg] {
  input.resource.tags.data_classification == "PII"
  input.resource.properties.location in ["eastus", "westus"]
  msg := "PII data must be stored in compliant regions (not East US or West US)"
}

# Retention policies
deny[msg] {
  input.resource.type == "storage_account"
  input.resource.tags.data_classification == "PII"
  input.resource.properties.retention_days < 2555  # 7 years
  msg := "PII data must be retained for minimum 7 years"
}
```

**Audit Requirements**:
```rego
# Enable audit logging
deny[msg] {
  input.resource.type in ["database", "storage_account"]
  not input.resource.properties.audit_logging
  msg := sprintf("%s must have audit logging enabled", [input.resource.type])
}
```

#### Naming Conventions

```rego
package platform.naming

# Resource naming pattern
deny[msg] {
  input.resource.type == "storage_account"
  not re_match("^[a-z0-9]{3,24}$", input.resource.name)
  msg := "Storage account name must be 3-24 lowercase alphanumeric characters"
}

# Tag requirements
deny[msg] {
  required_tag := ["team", "environment", "cost_center"]
  tag := required_tag[_]
  not input.resource.tags[tag]
  msg := sprintf("Resource must have '%s' tag", [tag])
}
```

### Policy Enforcement Points

```
┌──────────────────────────────────────────────┐
│         Policy Enforcement Points            │
├──────────────────────────────────────────────┤
│                                              │
│  1. Template Validation (Pre-provision)      │
│     └─ Validate variables                    │
│     └─ Check naming conventions              │
│     └─ Verify required tags                  │
│                                              │
│  2. Policy Engine (Pre-provision)            │
│     └─ Security policies                     │
│     └─ Cost policies                         │
│     └─ Compliance policies                   │
│     └─ OPA/Sentinel evaluation               │
│                                              │
│  3. Approval Workflow (Human-in-the-loop)    │
│     └─ Production deployments                │
│     └─ High-cost resources                   │
│     └─ Sensitive operations                   │
│                                              │
│  4. Admission Controller (Runtime)           │
│     └─ Kubernetes manifest validation        │
│     └─ Image scanning                        │
│     └─ Resource quotas                       │
│                                              │
│  5. Continuous Compliance (Post-provision)   │
│     └─ Drift detection                       │
│     └─ Periodic audits                       │
│     └─ Anomaly detection                     │
│                                              │
└──────────────────────────────────────────────┘
```

## Approval Workflows

### Approval Matrix

| Resource Type | Environment | Approvers | SLA |
|---------------|-------------|-----------|-----|
| Data Lake | dev | None | - |
| Data Lake | staging | Data Team Lead | 4 hours |
| Data Lake | prod | Data Team Lead + Platform Lead | 8 hours |
| Kafka Cluster | dev | None | - |
| Kafka Cluster | prod | Platform Team + SRE | 8 hours |
| ML Model Deployment | any | ML Lead | 4 hours |
| Infrastructure Changes | prod | Platform + SRE | 8 hours |
| Cost > $1000/month | any | Finance | 24 hours |
| Security-sensitive | any | Security Team | 24 hours |

### Approval Process

```
Request Submitted
  ↓
Automatic Validation
  ├─ Policy check
  ├─ Cost estimation
  └─ Resource availability
  ↓
Approval Required?
  ├─ No → Provision
  └─ Yes → Notify Approvers
            ↓
          Approvers Review
            ↓
          Decision
            ├─ Approved → Provision
            ├─ Rejected → Notify Requester
            └─ Pending → Escalate (SLA)
```

### Approval Notification

```yaml
# Slack notification example
notifications:
  - type: slack
    channel: "#platform-approvals"
    template: |
      Approval Required
      Resource: {{resource_name}}
      Type: {{resource_type}}
      Environment: {{environment}}
      Requested by: {{requester}}
      Estimated cost: {{estimated_cost}}/month
      Approve: {{approval_url}}
      Review dashboard: {{dashboard_url}}
```

## Audit & Compliance

### Audit Logging

All platform actions are logged:

```json
{
  "timestamp": "2026-01-03T12:00:00Z",
  "event_id": "uuid",
  "event_type": "resource.provisioned",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "team": "data-team"
  },
  "resource": {
    "id": "resource-456",
    "type": "storage_account",
    "name": "my-data-lake"
  },
  "action": {
    "type": "provision",
    "parameters": {
      "template": "data-lake-medallion",
      "environment": "prod"
    }
  },
  "result": {
    "status": "success",
    "duration_ms": 1500,
    "outputs": {...}
  },
  "metadata": {
    "ip_address": "192.168.1.1",
    "user_agent": "platform-cli/1.0.0"
  }
}
```

### Compliance Reports

**Monthly Compliance Report**:
```yaml
report:
  period: "2026-01"
  team: "data-team"

  summary:
    total_resources: 45
    compliant_resources: 43
    non_compliant: 2
    compliance_rate: 95.6%

  violations:
    - resource: "storage-old"
      policy: "encryption-required"
      severity: "high"
      status: "open"

    - resource: "vm-test"
      policy: "auto-shutdown"
      severity: "low"
      status: "open"

  recommendations:
    - "Enable encryption for storage-old"
    - "Enable auto-shutdown for vm-test"
    - "Review and update tags for 3 resources"
```

### GDPR/Privacy Compliance

**Data Classification**:
```python
DATA_CLASSIFICATION = {
    "public": {
        "encryption": "optional",
        "retention": "1 year",
        "access": "everyone"
    },
    "internal": {
        "encryption": "required",
        "retention": "3 years",
        "access": "employees"
    },
    "confidential": {
        "encryption": "required",
        "retention": "7 years",
        "access": "need-to-know"
    },
    "PII": {
        "encryption": "required",
        "retention": "7 years",
        "access": "restricted",
        "audit": "full",
        "data_residency": "compliant-regions-only"
    }
}
```

## Cost Governance

### Cost Allocation

**Tagging Strategy**:
```yaml
required_tags:
  - team: "Team name (e.g., data-team, ml-team)"
  - environment: "dev|staging|prod"
  - cost_center: "Cost center code"
  - project: "Project name"
  - owner: "Owner email"

optional_tags:
  - data_classification: "public|internal|confidential|PII"
  - backup_policy: "daily|weekly|monthly"
  - retention_days: "Number"
```

**Cost Visibility**:
```bash
# Cost by team
platform costs --group-by team --last 30d

# Cost by project
platform costs --group-by project --last 30d

# Cost by environment
platform costs --group-by environment --last 30d

# Forecast
platform costs forecast --next 3m
```

### Budget Management

**Budget Alerts**:
```python
BUDGETS = {
    "data-team": {
        "monthly_limit": 5000,
        "alert_thresholds": [80, 90, 100],
        "actions": ["notify", "restrict"]
    },
    "ml-team": {
        "monthly_limit": 8000,
        "alert_thresholds": [80, 90, 100],
        "actions": ["notify", "restrict", "require_approval"]
    }
}
```

**Alert Actions**:
- 80%: Notify team
- 90%: Notify + require approval for new resources
- 100%: Block new resources + notify leadership

### Chargeback Model

```python
class ChargebackModel:
    """
    Cost allocation strategies
    """

    @staticmethod
    def direct_allocation(resource):
        """Direct cost to owning team"""
        team = resource.tags["team"]
        return {"team": team, "amount": resource.cost}

    @staticmethod
    def shared_allocation(resource, teams):
        """Split cost across teams"""
        cost_per_team = resource.cost / len(teams)
        return [{"team": team, "amount": cost_per_team} for team in teams]

    @staticmethod
    def usage_based_allocation(resource, usage):
        """Allocate based on usage"""
        total_usage = sum(usage.values())
        return {
            team: (usage[team] / total_usage) * resource.cost
            for team in usage
        }
```

## Security Governance

### Identity & Access Management

**SSO Integration**:
```python
SSO_PROVIDERS = {
    "azure_ad": {
        "client_id": "xxx",
        "tenant_id": "xxx",
        "scopes": ["openid", "profile", "email"]
    },
    "google": {
        "client_id": "xxx",
        "scopes": ["openid", "profile", "email"]
    },
    "github": {
        "client_id": "xxx",
        "scopes": ["user:email"]
    }
}
```

**RBAC Model**:
```yaml
roles:
  platform-admin:
    description: "Full platform access"
    permissions:
      - "*:*"

  team-admin:
    description: "Team administrator"
    permissions:
      - "team:read"
      - "team:write"
      - "resources:read"
      - "resources:write"
      - "members:read"
      - "members:write"

  developer:
    description: "Team developer"
    permissions:
      - "resources:read"
      - "resources:write"
      - "team:read"

  viewer:
    description: "Read-only access"
    permissions:
      - "resources:read"
      - "team:read"
```

### Secrets Management

**Vault Integration**:
```python
class SecretsManager:
    """
    Centralized secrets management
    """

    @staticmethod
    async def get_secret(path: str) -> str:
        """Retrieve secret from Vault"""
        pass

    @staticmethod
    async def set_secret(path: str, value: str):
        """Store secret in Vault"""
        pass

    @staticmethod
    async def rotate_secret(path: str):
        """Rotate secret"""
        pass

    @staticmethod
    async def grant_access(team: str, secret_path: str, ttl: int):
        """Grant temporary access to secret"""
        pass
```

**Secrets Rotation Policy**:
```yaml
rotation_policies:
  database_credentials:
    rotation_period: "90d"
    grace_period: "7d"
    notify_before: "30d"

  api_keys:
    rotation_period: "30d"
    grace_period: "7d"
    notify_before: "7d"

  certificates:
    rotation_period: "365d"
    grace_period: "30d"
    notify_before: "30d"
```

## Risk Management

### Risk Assessment

**Risk Matrix**:
```
Impact
  High    │  │R│  │R│  │R│
          │  │I│  │I│  │I│
  Medium  │  │S│  │S│  │S│
          │  │K│  │K│  │K│
  Low     │  │  │  │  │  │
          └────────────────
            Low  Medium  High
              Likelihood
```

**Risk Categories**:
1. **Security Risks**: Data breaches, unauthorized access
2. **Operational Risks**: Outages, performance degradation
3. **Financial Risks**: Cost overruns, budget violations
4. **Compliance Risks**: Regulatory violations, audit failures

### Incident Response

**Severity Levels**:
```yaml
severity_levels:
  critical:
    description: "Complete service outage or data breach"
    response_time: "15 minutes"
    escalation: "immediate"
    examples:
      - "Production platform down"
      - "Data breach detected"
      - "Security incident"

  high:
    description: "Major service degradation"
    response_time: "1 hour"
    escalation: "1 hour"
    examples:
      - "Provisioning system down"
      - "Database unavailable"
      - "Authentication system down"

  medium:
    description: "Minor service degradation"
    response_time: "4 hours"
    escalation: "8 hours"
    examples:
      - "Single template failing"
      - "Non-critical service down"
      - "Performance degradation"

  low:
    description: "Cosmetic issues or enhancements"
    response_time: "24 hours"
    escalation: "none"
    examples:
      - "Documentation error"
      - "UI bug"
      - "Feature request"
```

**Incident Response Process**:
```
1. Detection
   ├─ Automated alert
   ├─ User report
   └─ Monitoring system

2. Triage
   ├─ Assess severity
   ├─ Assign owner
   └─ Create incident

3. Mitigation
   ├─ Immediate fix
   ├─ Workaround
   └─ Communication

4. Resolution
   ├─ Root cause fix
   ├─ Testing
   └─ Deployment

5. Post-Mortem
   ├─ Timeline
   ├─ Root cause
   ├─ Action items
   └─ Documentation
```

## Platform Health

### Health Checks

```python
class PlatformHealthCheck:
    """
    Comprehensive platform health monitoring
    """

    @staticmethod
    async def check_database():
        """Check database connectivity"""
        try:
            await database.health_check()
            return {"status": "healthy", "latency_ms": 5}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    async def check_cache():
        """Check Redis cache"""
        try:
            await redis.ping()
            return {"status": "healthy", "latency_ms": 1}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    async def check_kubernetes():
        """Check Kubernetes API"""
        try:
            await kubernetes.get_nodes()
            return {"status": "healthy", "nodes": 10}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    @staticmethod
    async def check_provisioning():
        """Check provisioning service"""
        try:
            # Test provisioning pipeline
            return {"status": "healthy", "queue_length": 0}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
```

### Service Level Objectives (SLOs)

```yaml
slos:
  api_availability:
    target: 99.9%
    measurement: "uptime"
    window: "30d"

  api_latency:
    target: 200ms
    percentile: p95
    measurement: "response_time"

  provisioning_success_rate:
    target: 95%
    measurement: "successful_provisions / total_provisions"
    window: "7d"

  provisioning_time:
    target: 300s
    percentile: p95
    measurement: "time_from_request_to_completion"

  policy_evaluation_time:
    target: 5s
    percentile: p95
    measurement: "time_to_evaluate_policies"
```

## Monitoring & Alerting

### Platform Metrics

**Key Metrics**:
- Provisioning request rate
- Provisioning success rate
- Policy violation rate
- API latency (p50, p95, p99)
- API error rate
- Active users
- Template usage
- Cost per team

**Alerting Rules**:
```yaml
alerts:
  - name: HighErrorRate
    condition: error_rate > 0.05
    duration: 5m
    severity: critical
    action: page

  - name: HighLatency
    condition: p95_latency > 500ms
    duration: 5m
    severity: warning
    action: notify

  - name: ProvisioningFailures
    condition: provisioning_failure_rate > 0.1
    duration: 10m
    severity: high
    action: page

  - name: BudgetExceeded
    condition: current_spend > budget
    duration: 0m
    severity: critical
    action: notify

  - name: PolicyViolations
    condition: policy_violations > 10
    duration: 1h
    severity: warning
    action: notify
```

### Dashboards

**Platform Health Dashboard**:
- Overall health status
- Service availability
- Request rate and latency
- Error rate
- Active incidents

**Governance Dashboard**:
- Policy compliance rate
- Open violations
- Approval queue
- Audit log events
- Cost tracking

**Developer Dashboard**:
- Active users
- Self-service adoption
- Time to provision
- Template popularity
- Support tickets

## Continuous Improvement

### Policy Reviews

**Quarterly Review**:
- Review policy effectiveness
- Update based on incidents
- Optimize for developer experience
- Align with business needs

**Annual Review**:
- Strategic assessment
- Industry best practices
- Technology refresh
- Cost optimization

### Metrics Review

**Weekly**:
- Review alerts
- Check SLOs
- Address violations
- Respond to incidents

**Monthly**:
- Compliance report
- Cost analysis
- Developer feedback
- Platform metrics

**Quarterly**:
- Business review
- ROI analysis
- Strategic planning
- Roadmap update

## References

- [Security Policies](security.md)
- [Cost Management](cost-management.md)
- [Compliance Requirements](compliance.md)
- [Incident Response Runbook](runbooks/incident-response.md)