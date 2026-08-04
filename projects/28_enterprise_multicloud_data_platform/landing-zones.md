# Cloud Landing Zones

## Table of Contents

1. [Landing Zone Overview](#landing-zone-overview)
2. [Azure Landing Zone](#azure-landing-zone)
3. [AWS Landing Zone](#aws-landing-zone)
4. [Landing Zone Comparison](#landing-zone-comparison)
5. [Shared Landing Zone Patterns](#shared-landing-zone-patterns)
6. [Landing Zone Automation](#landing-zone-automation)
7. [Landing Zone Governance](#landing-zone-governance)
8. [Best Practices](#best-practices)

---

## Landing Zone Overview

A landing zone is a well-architected, multi-account environment that provides a foundation for cloud workloads. It includes network architecture, identity management, security controls, governance policies, and operational tooling.

### Landing Zone Components

**Core Components**
- Identity and Access Management
- Network Topology and Connectivity
- Security Baseline and Policies
- Monitoring and Logging
- Cost Management and Budgets
- Backup and Disaster Recovery

**Platform Components**
- Kubernetes Infrastructure
- Data Platform Services
- AI/ML Services
- CI/CD Pipelines
- Developer Tools

**Governance Components**
- Policy as Code
- Compliance Monitoring
- Audit Logging
- Resource Tagging
- Change Management

---

## Azure Landing Zone

### Architecture Overview

```
Azure Landing Zone (Enterprise-Scale)
├── Management Group Hierarchy
│   ├── Root
│   │   └── Platform Management Group
│   │       ├── Identity Subscription
│   │       ├── Management Subscription
│   │       └── Connectivity Subscription
│   └── Landing Zone Management Group
│       ├── Data Platform Landing Zone
│       │   ├── Development
│   │   ├── Staging
│   │   └── Production
│       └── AI Platform Landing Zone
│           ├── Development
│           ├── Staging
│           └── Production
│
├── Platform Services
│   ├── Azure Active Directory
│   ├── Azure Monitor
│   ├── Azure Policy
│   └── Azure Security Center
│
└── Network Topology
    ├── Azure Virtual WAN
    ├── Virtual Hubs
    ├── ExpressRoute Connections
    └── VPN Gateways
```

### Implementation

**Management Groups**
```hcl
# Create management group hierarchy
resource "azuread_group" "platform_owners" {
  display_name     = "Platform Owners"
  security_enabled = true
}

resource "azurerm_management_group" "platform" {
  display_name = "Platform"
  parent_management_group_id = data.azurerm_management_group.root.id

  lifecycle {
    ignore_changes = [parent_management_group_id]
  }
}

resource "azurerm_management_group" "landing_zones" {
  display_name = "Landing Zones"
  parent_management_group_id = azurerm_management_group.platform.id
}

resource "azurerm_management_group" "data_platform" {
  display_name = "Data Platform"
  parent_management_group_id = azurerm_management_group.landing_zones.id
}

resource "azurerm_management_group" "ai_platform" {
  display_name = "AI Platform"
  parent_management_group_id = azurerm_management_group.landing_zones.id
}
```

**Identity Subscription**
```hcl
module "identity_subscription" {
  source = "./modules/azure/identity-subscription"

  management_group_id = azurerm_management_group.platform.id
  subscription_name   = "plat-identity-prod-001"

  # Azure AD configuration
  enable_azure_ad_connect = true
  enable_privileged_identity_management = true

  # Security settings
  enable_defender = true
  enable_sentinel = true

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}
```

**Connectivity Subscription**
```hcl
module "connectivity_subscription" {
  source = "./modules/azure/connectivity-subscription"

  management_group_id = azurerm_management_group.platform.id
  subscription_name   = "plat-connectivity-prod-001"

  # Network configuration
  virtual_wan = {
    enabled     = true
    sku         = "Standard"
    branch_count = 10
  }

  # VPN configuration
  express_route = {
    enabled = true
    bandwidth_gbps = 10
  }

  # DNS configuration
  private_dns_zones = [
    "privatelink.blob.core.windows.net",
    "privatelink.database.windows.net"
  ]

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}
```

**Data Platform Landing Zone**
```hcl
module "data_platform_landing_zone" {
  source = "./modules/azure/data-platform-landing-zone"

  management_group_id = azurerm_management_group.data_platform.id
  subscription_name   = "plat-data-prod-001"

  # Environment configurations
  environments = {
    development = {
      location = "East US"
      cidr_range = "10.0.0.0/16"
    }
    staging = {
      location = "East US 2"
      cidr_range = "10.1.0.0/16"
    }
    production = {
      location = "West Europe"
      cidr_range = "10.2.0.0/16"
    }
  }

  # Data platform services
  data_services = {
    storage = {
      enabled = true
      encryption_enabled = true
    }
    data_factory = {
      enabled = true
    }
    databricks = {
      enabled = true
      workspace_sku = "premium"
    }
    synapse = {
      enabled = true
    }
  }

  # Security configuration
  security = {
    enable_defender = true
    enable_encryption = true
    enable_audit_logging = true
    enable_private_endpoints = true
  }

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}
```

### Network Architecture

**Hub-and-Spoke Topology**
```hcl
# Hub VNet
resource "azurerm_virtual_network" "hub" {
  name                = "vnet-hub-prod-001"
  address_space       = ["10.255.0.0/16"]
  location            = var.location
  resource_group_name = azurerm_resource_group.hub.name

  tags = {
    environment = "production"
    role        = "hub"
  }
}

# Spoke VNet for Data Platform
resource "azurerm_virtual_network" "data_platform" {
  name                = "vnet-data-platform-prod-001"
  address_space       = ["10.0.0.0/16"]
  location            = var.location
  resource_group_name = azurerm_resource_group.data_platform.name

  tags = {
    environment = "production"
    role        = "spoke"
  }
}

# VNet Peering
resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  name                      = "peer-hub-to-data-platform"
  resource_group_name        = azurerm_resource_group.hub.name
  virtual_network_name       = azurerm_virtual_network.hub.name
  remote_virtual_network_id  = azurerm_virtual_network.data_platform.id
  allow_forwarded_traffic    = true
  allow_gateway_transit      = false
  use_remote_gateways        = true
}

resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "peer-data-platform-to-hub"
  resource_group_name       = azurerm_resource_group.data_platform.name
  virtual_network_name      = azurerm_virtual_network.data_platform.name
  remote_virtual_network_id = azurerm_virtual_network.hub.id
  allow_forwarded_traffic   = true
  allow_gateway_transit     = true
  use_remote_gateways       = false
}
```

### Security Baseline

**Azure Policy Definitions**
```hcl
# Require encryption at rest
resource "azurerm_policy_definition" "require_encryption" {
  name         = "require-encryption-at-rest"
  display_name = "Require encryption at rest for data resources"
  description  = "This policy ensures encryption is enabled for data resources"
  policy_type  = "Custom"
  mode         = "Indexed"

  policy_rule = <<POLICY
    {
      "if": {
        "anyOf": [
          {
            "field": "type",
            "in": [
              "Microsoft.Storage/storageAccounts",
              "Microsoft.Sql/servers/databases",
              "Microsoft.KeyVault/vaults"
            ]
          }
        ]
      },
      "then": {
        "effect": "deny",
        "details": {
          "field": "Microsoft.Storage/storageAccounts/encryption",
          "value": true
        }
      }
    }
  POLICY
}

# Deny public network access
resource "azurerm_policy_definition" "deny_public_network" {
  name         = "deny-public-network-access"
  display_name = "Deny public network access for data resources"
  description  = "This policy denies creation of resources with public network access"
  policy_type  = "Custom"
  mode         = "Indexed"

  policy_rule = <<POLICY
    {
      "if": {
        "field": "Microsoft.Storage/storageAccounts/networkAcls.allowBlobPublicAccess",
        "equals": true
      },
      "then": {
        "effect": "deny"
      }
    }
  POLICY
}
```

**Security Center Configuration**
```hcl
# Enable Defender for storage
resource "azurerm_security_center_storage_defender" "data_platform" {
  storage_account_id = azurerm_storage_account.data_platform.id
  setting = {
    enabled = true
    sensitive_data_discovery = {
      enabled = true
    }
  }
}

# Enable Defender for databases
resource "azurerm_security_center_sql_defender" "synapse" {
  server_name        = azurerm_synapse_workspace.data_platform.name
  resource_group_name = azurerm_synapse_workspace.data_platform.resource_group_name

  setting {
    storage_auto_discovery = {
      enabled = true
    }
  }
}
```

---

## AWS Landing Zone

### Architecture Overview

```
AWS Landing Zone (Enterprise-Scale)
├── AWS Organizations
│   ├── Root
│   ├── Security OU
│   │   ├── Log Archive Account
│   │   └── Security Tooling Account
│   ├── Infrastructure OU
│   │   ├── Network Account
│   │   └── Shared Services Account
│   └── Workloads OU
│       ├── Data Platform OU
│       │   ├── Development
│       │   ├── Staging
│       │   └── Production
│       └── AI Platform OU
│           ├── Development
│           ├── Staging
│           └── Production
│
├── AWS Services
│   ├── AWS IAM Identity Center
│   ├── AWS Config
│   ├── AWS CloudTrail
│   ├── Amazon GuardDuty
│   └── AWS Security Hub
│
└── Network Topology
    ├── AWS Transit Gateway
    ├── VPCs
    ├── Direct Connect
    └── VPN Connections
```

### Implementation

**AWS Organizations**
```hcl
# Create organizational units
resource "aws_organizations_organizational_unit" "security" {
  name      = "Security"
  parent_id = aws_organizations_organization.root.roots[0].id
}

resource "aws_organizations_organizational_unit" "infrastructure" {
  name      = "Infrastructure"
  parent_id = aws_organizations_organization.root.roots[0].id
}

resource "aws_organizations_organizational_unit" "workloads" {
  name      = "Workloads"
  parent_id = aws_organizations_organization.root.roots[0].id
}

resource "aws_organizations_organizational_unit" "data_platform" {
  name      = "Data Platform"
  parent_id = aws_organizations_organizational_unit.workloads.id
}

# Create accounts
resource "aws_organizations_account" "data_prod" {
  name  = "data-prod-001"
  email = "data-prod@company.com"

  parent_id = aws_organizations_organizational_unit.data_platform.id

  tags = {
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}
```

**Network Account**
```hcl
module "network_account" {
  source = "./modules/aws/network-account"

  account_name = "network-prod-001"
  organization_unit = aws_organizations_organizational_unit.infrastructure.id

  # Transit Gateway
  transit_gateway = {
    enabled = true
    amazon_side_asn = 64512
  }

  # VPC Configuration
  vpcs = {
    data_platform = {
      cidr_block = "10.1.0.0/16"
      azs        = ["us-east-1a", "us-east-1b", "us-east-1c"]
      public_subnets  = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
      private_subnets = ["10.1.11.0/24", "10.1.12.0/24", "10.1.13.0/24"]
      data_subnets    = ["10.1.21.0/24", "10.1.22.0/24", "10.1.23.0/24"]
    }
  }

  # Direct Connect
  direct_connect = {
    enabled = true
    bandwidth_gbps = 10
  }

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}
```

**Data Platform Account**
```hcl
module "data_platform_account" {
  source = "./modules/aws/data-platform-account"

  account_name = "data-prod-001"
  organization_unit = aws_organizations_organizational_unit.data_platform.id

  # S3 Configuration
  s3 = {
    enabled = true
    encryption = true
    versioning = true
    access_logging = true
  }

  # EKS Configuration
  eks = {
    enabled = true
    kubernetes_version = "1.28"
    node_groups = {
      general = {
        instance_types = ["m5.xlarge"]
        min_size = 3
        max_size = 10
      }
      compute = {
        instance_types = ["c5.2xlarge"]
        min_size = 0
        max_size = 20
      }
    }
  }

  # Data services
  data_services = {
    glue = {
      enabled = true
    }
    redshift = {
      enabled = true
    }
    emr = {
      enabled = true
    }
  }

  # Security
  security = {
    enable_guardduty = true
    enable_security_hub = true
    enable_config = true
    enable_cloudtrail = true
  }

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}
```

### Security Baseline

**AWS Config Rules**
```hcl
# S3 bucket encryption
resource "aws_config_config_rule" "s3_bucket_encryption" {
  name = "s3-bucket-encryption-enabled"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
  }

  depends_on = [aws_config_configuration_recorder.recorder]
}

# S3 bucket public access
resource "aws_config_config_rule" "s3_bucket_public_access" {
  name = "s3-bucket-public-access-prohibited"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_ACCESS_PROHIBITED"
  }

  depends_on = [aws_config_configuration_recorder.recorder]
}

# IAM password policy
resource "aws_config_config_rule" "iam_password_policy" {
  name = "iam-password-policy"

  source {
    owner             = "AWS"
    source_identifier = "IAM_PASSWORD_POLICY"
  }

  depends_on = [aws_config_configuration_recorder.recorder]
}
```

**IAM Identity Center**
```hcl
# Enable IAM Identity Center
resource "aws_ssoadmin_instances" "sso" {}

# Permission sets
resource "aws_ssoadmin_permission_set" "data_engineer" {
  name         = "DataEngineer"
  instance_arn = tolist(aws_ssoadmin_instances.sso.arns)[0]

  inline_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      }
    ]
  })
}

# Account assignments
resource "aws_ssoadmin_account_assignment" "data_engineer" {
  instance_arn       = tolist(aws_ssoadmin_instances.sso.arns)[0]
  permission_set_arn = aws_ssoadmin_permission_set.data_engineer.arn
  principal_id       = "data-engineer-group-id"
  principal_type     = "GROUP"
  target_id          = aws_organizations_account.data_prod.id
  target_type        = "AWS_ACCOUNT"
}
```

---

## Landing Zone Comparison

### Azure vs AWS

| Component | Azure | AWS |
|-----------|-------|-----|
| **Management Hierarchy** | Management Groups | Organizations + OUs |
| **Identity** | Azure AD | IAM Identity Center |
| **Networking** | Virtual WAN | Transit Gateway |
| **Policy Engine** | Azure Policy | AWS Config Rules |
| **Security** | Microsoft Defender | GuardDuty, Security Hub |
| **Compliance** | Compliance Manager | Artifact, Audit Manager |
| **Cost Management** | Cost Management | Cost Explorer, Budgets |
| **Monitoring** | Azure Monitor | CloudWatch |

### Feature Parity Matrix

| Feature | Azure | AWS | Notes |
|---------|-------|-----|-------|
| **Multi-account** | Subscriptions | Organizations | Both support multiple accounts |
| **Identity Federation** | Azure AD | IAM Identity Center | Both support SAML/OIDC |
| **Network Peering** | VNet Peering | VPC Peering | Similar capabilities |
| **Private Connectivity** | ExpressRoute | Direct Connect | Equivalent services |
| **Encryption** | Built-in | Built-in | Both support BYOK |
| **Audit Logging** | Azure Monitor | CloudTrail | Both comprehensive |
| **Policy as Code** | Azure Policy | AWS Config | Both support custom rules |

---

## Shared Landing Zone Patterns

### Naming Conventions

**Resource Naming**
```
Format: {env}-{service}-{region}-{instance}

Examples:
- prod-data-platform-east-001
- dev-data-platform-west-002
- staging-ai-platform-eu-003

Environment Prefixes:
- dev: Development
- stg: Staging
- prod: Production
- dr: Disaster Recovery

Service Names:
- data-platform: Data platform workloads
- ai-platform: AI/ML workloads
- identity: Identity services
- networking: Network infrastructure
```

**Tagging Strategy**
```yaml
Required Tags:
  - Environment: dev | staging | production | dr
  - Service: data-platform | ai-platform | identity
  - Owner: team-name
  - ManagedBy: terraform | manual
  - CostCenter: cost-center-code
  - Compliance: pci | hipaa | gdpr | none

Optional Tags:
  - Project: project-name
  - Team: team-name
  - Application: application-name
```

### Networking Patterns

**IP Address Management**

Azure:
```
VNet: 10.255.0.0/16
├── Subnets:
│   ├── Management: 10.255.0.0/24
│   ├── Gateway: 10.255.1.0/24
│   ├── AKS: 10.255.10.0/16 ( pods)
│   ├── AKS: 10.255.11.0/16 (services)
│   └── Data: 10.255.20.0/24
```

AWS:
```
VPC: 10.1.0.0/16
├── Subnets:
│   ├── Management: 10.1.0.0/24
│   ├── Public: 10.1.1.0/24
│   ├── Private: 10.1.10.0/24
│   ├── EKS: 10.1.11.0/16 (pods)
│   └── Data: 10.1.20.0/24
```

### Security Patterns

**Identity Patterns**
```
Primary IdP: Azure AD
├── Users and Groups
├── Multi-Factor Authentication (MFA)
├── Conditional Access
└── Privileged Identity Management (PIM)

Federated IdPs:
├── AWS IAM (SAML federation)
├── On-premises AD (Azure AD Connect)
└── External partners (B2B)

Service Principals:
├── Azure: Enterprise Applications
├── AWS: IAM Roles
└── Cross-cloud: Federated credentials
```

**Encryption Patterns**
```
Encryption at Rest:
├── Azure: Storage Service Encryption (SSE)
├── AWS: Server-Side Encryption (SSE)
├── Keys: Customer-managed keys (CMK)
└── Rotation: 90 days

Encryption in Transit:
├── TLS 1.3 minimum
├── mTLS for internal communication
└── Certificate rotation: 30 days
```

---

## Landing Zone Automation

### Terraform Modules

**Module Structure**
```
terraform/
├── modules/
│   ├── azure/
│   │   ├── landing-zone/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── versions.tf
│   │   ├── networking/
│   │   ├── identity/
│   │   └── security/
│   ├── aws/
│   │   ├── landing-zone/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── versions.tf
│   │   ├── networking/
│   │   ├── identity/
│   │   └── security/
│   └── shared/
│       ├── networking/
│       ├── security/
│       └── monitoring/
```

**Module Usage**
```hcl
# Azure landing zone
module "azure_landing_zone" {
  source = "../../modules/azure/landing-zone"

  management_group_id = azurerm_management_group.data_platform.id
  subscription_name   = "plat-data-prod-001"

  # Networking
  vnet_cidr = "10.0.0.0/16"
  subnets = {
    aks    = "10.0.1.0/24"
    data   = "10.0.2.0/24"
    mgmt   = "10.0.3.0/24"
  }

  # Security
  enable_defender = true
  enable_encryption = true
  enable_audit_logging = true

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}

# AWS landing zone
module "aws_landing_zone" {
  source = "../../modules/aws/landing-zone"

  organization_unit_id = aws_organizations_organizational_unit.data_platform.id
  account_name         = "data-prod-001"

  # Networking
  vpc_cidr = "10.1.0.0/16"
  subnets = {
    eks     = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
    data    = ["10.1.11.0/24", "10.1.12.0/24", "10.1.13.0/24"]
    private = ["10.1.21.0/24", "10.1.22.0/24", "10.1.23.0/24"]
  }

  # Security
  enable_guardduty = true
  enable_security_hub = true
  enable_config = true
  enable_cloudtrail = true

  tags = {
    environment = "production"
    managed_by  = "terraform"
  }
}
```

### CI/CD Integration

**GitHub Actions Workflow**
```yaml
name: Landing Zone Deployment

on:
  push:
    branches: [main]
    paths:
      - 'landing-zones/**'
      - 'terraform/modules/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.5.0

      - name: Terraform Init
        run: terraform init
        working-directory: ./landing-zones

      - name: Terraform Validate
        run: terraform validate
        working-directory: ./landing-zones

      - name: Terraform Plan
        run: terraform plan -out=tfplan
        working-directory: ./landing-zones
        env:
          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          ARM_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
        working-directory: ./landing-zones
        env:
          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          ARM_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}

  deploy-aws:
    runs-on: ubuntu-latest
    needs: validate
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.5.0

      - name: Terraform Init
        run: terraform init
        working-directory: ./landing-zones/aws

      - name: Terraform Apply
        run: terraform apply -auto-approve
        working-directory: ./landing-zones/aws
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
```

---

## Landing Zone Governance

### Policy Enforcement

**Azure Policy**
```hcl
# Policy initiative for data platform
resource "azurerm_policy_initiative" "data_platform" {
  name         = "data-platform-policies"
  display_name = "Data Platform Policies"
  description  = "Policies for data platform landing zone"

  parameters = {
    allowedLocations = {
      value = ["East US", "East US 2", "West Europe"]
    }
  }

  policy_definition_reference {
    policy_definition_id = azurerm_policy_definition.require_encryption.id
  }

  policy_definition_reference {
    policy_definition_id = azurerm_policy_definition.deny_public_network.id
  }
}

# Assign policy to management group
resource "azurerm_policy_assignment" "data_platform" {
  name                 = "data-platform-policies"
  scope                = azurerm_management_group.data_platform.id
  policy_definition_id = azurerm_policy_initiative.data_platform.id
}
```

**AWS Service Control Policies (SCP)**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnauthorizedRegions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-east-2",
            "eu-west-1"
          ]
        }
      }
    },
    {
      "Sid": "DenyUnencryptedData",
      "Effect": "Deny",
      "Action": [
        "s3:PutObject",
        "rds:CreateDBInstance"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

### Compliance Monitoring

**Multi-Cloud Compliance Dashboard**
```python
class LandingZoneComplianceMonitor:
    """
    Monitor landing zone compliance across clouds
    """

    def __init__(self):
        self.azure_compliance = AzurePolicyComplianceChecker()
        self.aws_compliance = AWSConfigComplianceChecker()
        self.dashboard = ComplianceDashboard()

    async def check_compliance(self) -> ComplianceReport:
        """Check compliance for all landing zones"""
        azure_results = await self.azure_compliance.check_all()
        aws_results = await self.aws_compliance.check_all()

        report = ComplianceReport(
            timestamp=datetime.utcnow(),
            azure=azure_results,
            aws=aws_results,
            overall_compliance=(
                azure_results.compliance_percentage +
                aws_results.compliance_percentage
            ) / 2
        )

        await self.dashboard.update(report)

        return report
```

---

## Best Practices

### Landing Zone Design

1. **Start with Security Foundation**
   - Identity and access management
   - Network security
   - Encryption everywhere
   - Audit logging

2. **Implement Governance Early**
   - Policy as code
   - Automated compliance checks
   - Resource tagging
   - Cost allocation

3. **Design for Scale**
   - Multi-region from day one
   - Auto-scaling capabilities
   - Elastic networking
   - Global load balancing

4. **Enable Self-Service**
   - Developer portals
   - Golden paths
   - Automated provisioning
   - Documentation

### Automation Strategy

1. **Infrastructure as Code**
   - Terraform for all resources
   - Git-based workflows
   - Peer review process
   - Automated testing

2. **GitOps**
   - ArgoCD for deployments
   - declarative configuration
   - Automated sync
   - Rollback capabilities

3. **Continuous Compliance**
   - Policy validation in CI/CD
   - Automated compliance scans
   - Drift detection
   - Remediation automation

### Operational Excellence

1. **Monitoring**
   - Unified observability
   - Proactive alerting
   - SLO definitions
   - Incident response

2. **Cost Management**
   - Budget alerts
   - Resource tagging
   - Right-sizing recommendations
   - Reserved capacity planning

3. **Security Operations**
   - Threat detection
   - Vulnerability scanning
   - Patch management
   - Incident response

---

## Conclusion

Landing zones provide a secure, scalable, and compliant foundation for cloud workloads. Implement them with automation, governance, and operational excellence in mind.

Key Takeaways:
- Start with strong security and governance foundations
- Automate everything with IaC and GitOps
- Standardize across environments and clouds
- Monitor continuously and optimize regularly