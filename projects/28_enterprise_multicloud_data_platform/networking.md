# Cross-Cloud Networking

## Table of Contents

1. [Networking Overview](#networking-overview)
2. [Network Architecture](#network-architecture)
3. [Azure Networking](#azure-networking)
4. [AWS Networking](#aws-networking)
5. [Cross-Cloud Connectivity](#cross-cloud-connectivity)
6. [DNS Strategy](#dns-strategy)
7. [Load Balancing](#load-balancing)
8. [Service Mesh](#service-mesh)
9. [Network Security](#network-security)
10. [Performance Optimization](#performance-optimization)

---

## Networking Overview

Cross-cloud networking provides secure, high-performance connectivity between Azure, AWS, and on-premises datacenters. It enables seamless communication between services across clouds while maintaining security, reliability, and performance.

### Networking Principles

**1. Zero Trust Networking**
- Never trust, always verify
- Identity-based access control
- Encryption everywhere
- Micro-segmentation

**2. High Availability**
- Redundant connections
- Automatic failover
- Load balancing
- Health checks

**3. Performance**
- Low latency routing
- Bandwidth optimization
- Traffic prioritization
- Global load balancing

**4. Security**
- Network segmentation
- Firewall rules
- DDoS protection
- Traffic inspection

---

## Network Architecture

### Global Network Topology

```
                    ┌──────────────────┐
                    │   On-Premises    │
                    │   Datacenter     │
                    └────────┬─────────┘
                             │
                    ExpressRoute/Direct Connect
                             │
                    ┌────────▼─────────┐
                    │  Cross-Cloud     │
                    │  Transit         │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
    │  Azure East    │ │ Azure West│ │  AWS      │
    │  US            │ │  Europe   │ │  US-East  │
    │  VNet: 10.0.0.0│ │ VNet:     │ │  VPC:     │
    │  /16           │ │ 10.0.1.0/│ │ 10.1.0.0/│
    │                │ │ 16        │ │ 16        │
    └────────────────┘ └───────────┘ └───────────┘
```

### Connectivity Patterns

**Hub-and-Spoke**
- Central transit gateway
- Spoke VNet/VPC per environment
- Centralized security and routing
- Simplified management

**Mesh**
- Direct cloud-to-cloud connections
- Lower latency for high-throughput
- More complex routing
- Higher cost

**Hybrid**
- Hub-and-spoke for most traffic
- Direct connections for critical workloads
- VPN as backup
- Cost-optimized

---

## Azure Networking

### Virtual Network Architecture

**VNet Design**
```hcl
# Hub VNet
resource "azurerm_virtual_network" "hub" {
  name                = "vnet-hub-prod-001"
  address_space       = ["10.255.0.0/16"]
  location            = var.location
  resource_group_name = azurerm_resource_group.networking.name

  tags = {
    environment = "production"
    role        = "hub"
  }
}

# Data Platform Spoke VNet
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

# Subnets
resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.data_platform.name
  virtual_network_name = azurerm_virtual_network.data_platform.name
  address_prefixes     = ["10.0.1.0/24"]

  delegations {
    name = "aks"
    service_delegation {
      name    = "Microsoft.ContainerService/managedClusters"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.data_platform.name
  virtual_network_name = azurerm_virtual_network.data_platform.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "snet-private-endpoints"
  resource_group_name  = azurerm_resource_group.data_platform.name
  virtual_network_name = azurerm_virtual_network.data_platform.name
  address_prefixes     = ["10.0.3.0/24"]

  private_endpoint_network_policies_enabled = false
}
```

### VNet Peering

**Hub-to-Spoke Peering**
```hcl
# Hub to spoke
resource "azurerm_virtual_network_peering" "hub_to_data_platform" {
  name                      = "peer-hub-to-data-platform"
  resource_group_name        = azurerm_resource_group.networking.name
  virtual_network_name       = azurerm_virtual_network.hub.name
  remote_virtual_network_id  = azurerm_virtual_network.data_platform.id
  allow_forwarded_traffic    = true
  allow_gateway_transit      = false
  use_remote_gateways        = true

  tags = {
    environment = "production"
  }
}

# Spoke to hub
resource "azurerm_virtual_network_peering" "data_platform_to_hub" {
  name                      = "peer-data-platform-to-hub"
  resource_group_name       = azurerm_resource_group.data_platform.name
  virtual_network_name      = azurerm_virtual_network.data_platform.name
  remote_virtual_network_id = azurerm_virtual_network.hub.id
  allow_forwarded_traffic   = true
  allow_gateway_transit     = true
  use_remote_gateways       = false

  tags = {
    environment = "production"
  }
}
```

### Azure Virtual WAN

**Global Transit Network**
```hcl
# Virtual WAN
resource "azurerm_virtual_wan" "wan" {
  name                = "vwan-prod-001"
  resource_group_name = azurerm_resource_group.networking.name
  location            = var.location
  type                = "Standard"

  tags = {
    environment = "production"
  }
}

# Virtual Hub
resource "azurerm_virtual_hub" "hub" {
  name                = "vhub-prod-001"
  resource_group_name = azurerm_resource_group.networking.name
  location            = var.location
  virtual_wan_id      = azurerm_virtual_wan.wan.id
  address_prefix      = "10.255.0.0/16"

  tags = {
    environment = "production"
  }
}

# VPN Gateway
resource "azurerm_vpn_gateway" "vpn" {
  name                = "vpn-gateway-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.networking.name
  virtual_hub_id      = azurerm_virtual_hub.hub.id
  bgp_route_translation_for_nat_enabled = true

  tags = {
    environment = "production"
  }
}

# ExpressRoute Gateway
resource "azurerm_express_route_gateway" "er_gateway" {
  name                = "er-gateway-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.networking.name
  virtual_hub_id      = azurerm_virtual_hub.hub.id
  scale_units         = 2

  tags = {
    environment = "production"
  }
}
```

### Network Security

**Network Security Groups**
```hcl
# NSG for AKS
resource "azurerm_network_security_group" "aks" {
  name                = "nsg-aks-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.data_platform.name

  security_rule {
    name                       = "allow-https"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    environment = "production"
  }
}

# Associate NSG with subnet
resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}
```

### Azure Firewall

**Centralized Firewall**
```hcl
# Azure Firewall
resource "azurerm_firewall" "firewall" {
  name                = "fw-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.networking.name
  sku_name            = "Premium"

  ip_configuration {
    name                 = "fw-ip-config"
    subnet_id            = azurerm_subnet.firewall.id
    public_ip_address_id = azurerm_public_ip.firewall.id
  }

  tags = {
    environment = "production"
  }
}

# Firewall Policy
resource "azurerm_firewall_policy" "policy" {
  name                = "fw-policy-prod-001"
  resource_group_name = azurerm_resource_group.networking.name
  location            = var.location

  threat_intel_mode = "Alert"

  dns {
    proxy_enabled = true
  }

  tags = {
    environment = "production"
  }
}

# Application Rule
resource "azurerm_firewall_policy_application_rule" "allow_azure" {
  firewall_policy_id = azurerm_firewall_policy.policy.id
  name               = "allow-azure-services"
  priority           = 100
  action             = "Allow"

  rule {
    name = "allow-azure"

    source_addresses = ["10.0.0.0/16", "10.1.0.0/16"]

    destination_fqdns = [
      "*.azure.com",
      "*.windows.net"
    ]

    protocol {
      port = "443"
      type = "Https"
    }
  }
}
```

---

## AWS Networking

### VPC Architecture

**VPC Design**
```hcl
# VPC
resource "aws_vpc" "data_platform" {
  cidr_block           = "10.1.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "vpc-data-platform-prod-001"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Subnets
resource "aws_subnet" "aks" {
  count             = 3
  vpc_id            = aws_vpc.data_platform.id
  cidr_block        = "10.1.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "subnet-eks-${count.index + 1}"
    "kubernetes.io/role/elb" = 1
  }
}

resource "aws_subnet" "data" {
  count             = 3
  vpc_id            = aws_vpc.data_platform.id
  cidr_block        = "10.1.${count.index + 11}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "subnet-data-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.data_platform.id
  cidr_block        = "10.1.${count.index + 21}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "subnet-private-${count.index + 1}"
  }
}
```

### VPC Peering

**Cross-Account Peering**
```hcl
# VPC Peering between AWS accounts
resource "aws_vpc_peering_connection" "data_to_ai" {
  vpc_id      = aws_vpc.data_platform.id
  peer_vpc_id = aws_vpc.ai_platform.id
  peer_owner_id = "123456789012"

  tags = {
    Name = "peer-data-to-ai"
  }
}

# Accept peering
resource "aws_vpc_peering_connection_accepter" "data_to_ai" {
  vpc_peering_connection_id = aws_vpc_peering_connection.data_to_ai.id
  auto_accept               = true
}

# Route table update
resource "aws_route" "data_to_ai" {
  route_table_id            = aws_route_table.data_platform.id
  destination_cidr_block    = "10.2.0.0/16"
  vpc_peering_connection_id = aws_vpc_peering_connection.data_to_ai.id
}
```

### AWS Transit Gateway

**Centralized Routing**
```hcl
# Transit Gateway
resource "aws_ec2_transit_gateway" "tgw" {
  description = "Transit Gateway for multi-cloud connectivity"
  amazon_side_asn = 64512

  tags = {
    Name        = "tgw-prod-001"
    Environment = "production"
  }
}

# TGW Attachment for VPC
resource "aws_ec2_transit_gateway_vpc_attachment" "data_platform" {
  subnet_ids         = [for s in aws_subnet.private : s.id]
  transit_gateway_id = aws_ec2_transit_gateway.tgw.id
  vpc_id             = aws_vpc.data_platform.id

  tags = {
    Name = "tgw-attachment-data-platform"
  }
}

# TGW Route Table
resource "aws_ec2_transit_gateway_route_table" "data_platform" {
  transit_gateway_id = aws_ec2_transit_gateway.tgw.id

  tags = {
    Name = "tgw-rt-data-platform"
  }
}

# Route
resource "aws_ec2_transit_gateway_route" "to_azure" {
  destination_cidr_block         = "10.0.0.0/16"
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.data_platform.id
  transit_gateway_route_table_id  = aws_ec2_transit_gateway_route_table.data_platform.id
}
```

### Network Security

**Security Groups**
```hcl
# Security group for EKS
resource "aws_security_group" "eks" {
  name        = "sg-eks-prod-001"
  description = "Security group for EKS cluster"
  vpc_id      = aws_vpc.data_platform.id

  # Allow HTTPS inbound
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sg-eks-prod-001"
  }
}

# Network ACL
resource "aws_network_acl" "data_platform" {
  vpc_id = aws_vpc.data_platform.id

  # Allow HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    rule_number = 100
    action      = "allow"
    cidr_block  = "0.0.0.0/0"
  }

  # Deny all
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    rule_number = 200
    action      = "deny"
    cidr_block  = "0.0.0.0/0"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    rule_number = 100
    action      = "allow"
    cidr_block  = "0.0.0.0/0"
  }

  tags = {
    Name = "nacl-data-platform"
  }
}
```

### AWS Network Firewall

**Advanced Firewall**
```hcl
# Network Firewall
resource "aws_networkfirewall_firewall" "firewall" {
  name                = "fw-prod-001"
  firewall_policy_arn = aws_networkfirewall_firewall_policy.policy.arn
  vpc_id              = aws_vpc.data_platform.id
  subnet_ids          = [aws_subnet.firewall[0].id]

  tags = {
    Name = "fw-prod-001"
  }
}

# Firewall Policy
resource "aws_networkfirewall_firewall_policy" "policy" {
  name = "fw-policy-prod-001"

  stateful_engine_options {
    rule_order = "STRICT_ORDER"
  }

  stateful_rule_group_reference {
    resource_arn = aws_networkfirewall_rule_group.threat_signatures.arn
  }

  stateless_rule_group_reference {
    resource_arn = aws_networkfirewall_rule_group.allow_https.arn
  }

  tags = {
    Name = "fw-policy-prod-001"
  }
}
```

---

## Cross-Cloud Connectivity

### VPN Configuration

**Azure VPN Gateway**
```hcl
resource "azurerm_virtual_network_gateway" "vpn" {
  name                = "vpn-gateway-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.networking.name

  type     = "Vpn"
  vpn_type = "RouteBased"
  sku      = "VpnGw1"
  active_active = false
  enable_bgp    = true
  bgp_route_translation_for_nat_enabled = true

  ip_configuration {
    name                          = "vnetGatewayConfig"
    public_ip_address_id          = azurerm_public_ip.vpn.id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.gateway.id
  }

  vpn_client_configuration {
    address_space = ["172.16.0.0/24"]
  }

  tags = {
    environment = "production"
  }
}
```

**AWS VPN Gateway**
```hcl
# VPN Gateway
resource "aws_vpn_gateway" "vpn" {
  vpc_id = aws_vpc.data_platform.id
  amazon_side_asn = 64512

  tags = {
    Name        = "vpn-gateway-prod-001"
    Environment = "production"
  }
}

# Customer Gateway (Azure side)
resource "aws_customer_gateway" "azure" {
  bgp_asn    = 65001
  ip_address = azurerm_public_ip.vpn.ip_address
  type       = "ipsec.1"

  tags = {
    Name = "cg-azure"
  }
}

# VPN Connection
resource "aws_vpn_connection" "azure" {
  vpn_gateway_id      = aws_vpn_gateway.vpn.id
  customer_gateway_id = aws_customer_gateway.azure.id
  type                = "ipsec.1"

  static_routes_only = false

  tags = {
    Name = "vpn-connection-azure"
  }
}
```

### Cross-Cloud Peering

**Azure to AWS Connection**
```python
class CrossCloudConnectivity:
    """
    Manage cross-cloud connectivity
    """

    def __init__(self):
        self.azure_network = AzureNetworkClient()
        self.aws_network = AWSNetworkClient()

    async def establish_peering(
        self,
        azure_vnet: str,
        aws_vpc: str
    ) -> PeeringResult:
        """Establish cross-cloud peering"""
        # Get Azure VNet
        vnet = await self.azure_network.get_vnet(azure_vnet)

        # Get AWS VPC
        vpc = await self.aws_network.get_vpc(aws_vpc)

        # Check if peering exists
        existing = await self._check_existing_peering(vnet, vpc)

        if existing:
            return existing

        # Create peering
        peering = await self._create_peering(vnet, vpc)

        # Configure routing
        await self._configure_routing(peering)

        # Verify connectivity
        await self._verify_connectivity(peering)

        return peering

    async def _create_peering(
        self,
        azure_vnet: VNet,
        aws_vpc: VPC
    ) -> PeeringResult:
        """Create cross-cloud peering"""
        # Implementation details
        pass
```

---

## DNS Strategy

### Azure DNS

**Private DNS Zones**
```hcl
# Private DNS Zone
resource "azurerm_private_dns_zone" "internal" {
  name                = "internal.company.com"
  resource_group_name = azurerm_resource_group.networking.name

  tags = {
    environment = "production"
  }
}

# Virtual Network Link
resource "azurerm_private_dns_zone_virtual_network_link" "data_platform" {
  name                  = "link-data-platform"
  resource_group_name   = azurerm_resource_group.networking.name
  private_dns_zone_name = azurerm_private_dns_zone.internal.name
  virtual_network_id    = azurerm_virtual_network.data_platform.id

  tags = {
    environment = "production"
  }
}

# A Record
resource "azurerm_private_dns_a_record" "databricks" {
  name                = "databricks"
  zone_name           = azurerm_private_dns_zone.internal.name
  resource_group_name = azurerm_resource_group.networking.name
  ttl                 = 300
  records             = ["10.0.2.4"]

  tags = {
    environment = "production"
  }
}
```

### AWS Route 53

**Private Hosted Zone**
```hcl
# Private Hosted Zone
resource "aws_route53_zone" "internal" {
  name = "internal.company.com"

  vpc {
    vpc_id = aws_vpc.data_platform.id
  }

  tags = {
    Environment = "production"
  }
}

# A Record
resource "aws_route53_record" "redshift" {
  zone_id = aws_route53_zone.internal.zone_id
  name    = "redshift"
  type    = "A"
  ttl     = "300"

  records = ["10.1.2.4"]
}

# Cross-cloud DNS routing
resource "aws_route53_record" "databricks_azure" {
  zone_id = aws_route53_zone.internal.zone_id
  name    = "databricks"
  type    = "A"
  ttl     = "300"

  # Route to Azure via VPN
  set_identifier = "azure"
  weight         = 100
  records        = ["10.0.2.4"]
}
```

### Unified DNS Strategy

**Cross-Cloud DNS**
```python
class UnifiedDNSManager:
    """
    Manage DNS across clouds
    """

    def __init__(self):
        self.azure_dns = AzureDNSClient()
        self.aws_dns = Route53Client()

    async def create_record(
        self,
        record: DNSRecord
    ):
        """Create DNS record across clouds"""
        # Create in Azure
        if record.cloud == "azure" or record.cross_cloud:
            await self.azure_dns.create_record(record)

        # Create in AWS
        if record.cloud == "aws" or record.cross_cloud:
            await self.aws_dns.create_record(record)

    async def resolve(
        self,
        hostname: str
    ) -> List[str]:
        """Resolve hostname across clouds"""
        # Try Azure DNS
        azure_ips = await self.azure_dns.resolve(hostname)

        # Try AWS DNS
        aws_ips = await self.aws_dns.resolve(hostname)

        # Return all IPs
        return list(set(azure_ips + aws_ips))
```

---

## Load Balancing

### Azure Load Balancer

**Standard Load Balancer**
```hcl
# Public Load Balancer
resource "azurerm_public_ip" "lb" {
  name                = "pip-lb-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.data_platform.name
  sku                 = "Standard"
  allocation_method   = "Static"

  tags = {
    environment = "production"
  }
}

# Load Balancer
resource "azurerm_lb" "lb" {
  name                = "lb-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.data_platform.name
  sku                 = "Standard"

  frontend_ip_configuration {
    name                 = "public"
    public_ip_address_id = azurerm_public_ip.lb.id
  }

  tags = {
    environment = "production"
  }
}

# Backend Pool
resource "azurerm_lb_backend_address_pool" "backend" {
  loadbalancer_id = azurerm_lb.lb.id
  name            = "backend"
}

# Health Probe
resource "azurerm_lb_probe" "health" {
  loadbalancer_id = azurerm_lb.lb.id
  name            = "health-probe"
  port            = 443
  protocol        = "Https"
  request_path    = "/health"
}

# Load Balancing Rule
resource "azurerm_lb_rule" "https" {
  loadbalancer_id                = azurerm_lb.lb.id
  name                           = "https-rule"
  protocol                       = "Tcp"
  frontend_port                  = 443
  backend_port                   = 443
  frontend_ip_configuration_name = "public"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.backend.id]
  probe_id                       = azurerm_lb_probe.health.id
}
```

### AWS Application Load Balancer

**Application Load Balancer**
```hcl
# ALB
resource "aws_lb" "alb" {
  name               = "alb-prod-001"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [for s in aws_subnet.aks : s.id]

  tags = {
    Name        = "alb-prod-001"
    Environment = "production"
  }
}

# Target Group
resource "aws_lb_target_group" "app" {
  name     = "tg-prod-001"
  port     = 443
  protocol = "HTTPS"
  vpc_id   = aws_vpc.data_platform.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200-299"
    path                = "/health"
    port                = "443"
    protocol            = "HTTPS"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "tg-prod-001"
  }
}

# Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
```

### Global Load Balancing

**Cross-Cloud Load Balancer**
```python
class GlobalLoadBalancer:
    """
    Global load balancing across clouds
    """

    def __init__(self):
        self.azure_lb = AzureLoadBalancer()
        self.aws_alb = AWSApplicationLoadBalancer()
        self.dns_manager = DNSManager()

    async def route_request(
        self,
        request: Request
    ) -> Response:
        """Route request to optimal endpoint"""
        # Determine user region
        user_region = self._get_user_region(request)

        # Get closest endpoint
        endpoint = await self._get_closest_endpoint(user_region)

        # Route request
        response = await endpoint.forward(request)

        return response

    async def _get_closest_endpoint(
        self,
        region: str
    ) -> Endpoint:
        """Get closest endpoint to user"""
        # Check Azure endpoints
        azure_endpoint = await self.azure_lb.get_endpoint(region)

        # Check AWS endpoints
        aws_endpoint = await self.aws_alb.get_endpoint(region)

        # Compare latency
        azure_latency = await self._measure_latency(azure_endpoint)
        aws_latency = await self._measure_latency(aws_endpoint)

        # Return faster endpoint
        if azure_latency < aws_latency:
            return azure_endpoint
        else:
            return aws_endpoint
```

---

## Service Mesh

### Istio Architecture

**Service Mesh Deployment**
```yaml
# Istio installation
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio
data:
  mesh: |-
    defaultConfig:
      discoveryAddress: istiod:15012
      proxyMetadata: {}
    enablePrometheusMerge: true
    defaultHttpRetryPolicy:
      numRetries: 3
      perTryTimeout: 2s
      retryOn: 5xx,gateway-error,connect-failure,refused-stream
```

**Virtual Service**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: data-platform
spec:
  hosts:
    - data-platform
  http:
    - route:
        - destination:
            host: data-platform
            port:
              number: 443
          weight: 80
        - destination:
            host: data-platform-azure
            port:
              number: 443
          weight: 20
      timeout: 30s
      retries:
        attempts: 3
        perTryTimeout: 2s
```

### mTLS Configuration

**Mutual TLS**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: data-platform
spec:
  selector:
    matchLabels:
      app: data-platform
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/data-platform/sa/data-platform"]
```

---

## Network Security

### DDoS Protection

**Azure DDoS Protection**
```hcl
# DDoS Protection Plan
resource "azurerm_network_ddos_protection_plan" "ddos" {
  name                = "ddos-plan-prod-001"
  location            = var.location
  resource_group_name = azurerm_resource_group.networking.name
  sku_name            = "Standard"

  tags = {
    environment = "production"
  }
}

# Associate with VNet
resource "azurerm_subnet" "aks" {
  # ... other configuration

  ddos_protection_plan_id = azurerm_network_ddos_protection_plan.ddos.id
}
```

**AWS Shield**
```hcl
# Enable Shield Advanced
resource "aws_shield_protection" "alb" {
  name         = "shield-alb-prod-001"
  resource_arn = aws_lb.alb.arn
}

# DDoS Resource Tier
resource "aws_shield_protection_group" "app" {
  name        = "shield-group-app"
  resource_group_id = aws_lb.alb.arn

  tags = {
    Name = "shield-group-app"
  }
}
```

### Web Application Firewall

**Azure WAF**
```hcl
# WAF Policy
resource "azurerm_web_application_firewall_policy" "waf" {
  name                = "waf-policy-prod-001"
  resource_group_name = azurerm_resource_group.networking.name
  location            = var.location

  managed_rules {
    managed_rule_set {
      version = "3.2"
      type    = "OWASP"
    }
  }

  policy_settings {
    enabled = true
    mode    = "Prevention"
  }

  tags = {
    environment = "production"
  }
}

# Associate with Application Gateway
resource "azurerm_web_application_firewall_policy_association" "appgw" {
  policy_id          = azurerm_web_application_firewall_policy.waf.id
  application_gateway_id = azurerm_application_gateway.appgw.id
}
```

**AWS WAF**
```hcl
# WAFv2
resource "aws_wafv2_web_acl" "waf" {
  name  = "waf-prod-001"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    action {
      block {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  tags = {
    Name        = "waf-prod-001"
    Environment = "production"
  }
}
```

---

## Performance Optimization

### Bandwidth Optimization

**Traffic Shaping**
```python
class TrafficOptimizer:
    """
    Optimize cross-cloud traffic
    """

    async def optimize_traffic(
        self,
        traffic: TrafficFlow
    ) -> OptimizedTraffic:
        """Optimize traffic flow"""
        # Analyze traffic patterns
        patterns = await self._analyze_patterns(traffic)

        # Apply optimization rules
        optimized = OptimizedTraffic()

        for flow in traffic.flows:
            # Choose optimal route
            route = await self._select_route(flow, patterns)

            # Apply QoS
            qos = await self._apply_qos(flow)

            optimized.add_flow(flow, route, qos)

        return optimized
```

### Caching Strategy

**Cross-Cloud CDN**
```python
class CrossCloudCDN:
    """
    Cross-cloud content delivery
    """

    def __init__(self):
        self.azure_cdn = AzureCDNClient()
        self.aws_cdn = AWSCloudFrontClient()

    async def cache_content(
        self,
        content: Content,
        regions: List[str]
    ):
        """Cache content across regions"""
        for region in regions:
            cloud = self._get_cloud_for_region(region)

            if cloud == "azure":
                await self.azure_cdn.cache(content, region)
            elif cloud == "aws":
                await self.aws_cdn.cache(content, region)
```

---

## Best Practices

### Network Design

1. **Use CIDR Blocks Efficiently**
   - Plan IP address allocation
   - Avoid overlapping CIDRs
   - Leave room for growth

2. **Implement Redundancy**
   - Multiple VPN connections
   - Redundant transit gateways
   - Failover automation

3. **Segment Networks**
   - Use subnets effectively
   - Apply NSGs/security groups
   - Implement micro-segmentation

4. **Monitor Performance**
   - Latency monitoring
   - Bandwidth utilization
   - Packet loss tracking

### Security

1. **Zero Trust Model**
   - Verify explicitly
   - Use least privilege
   - Assume breach

2. **Encrypt Traffic**
   - TLS 1.3 minimum
   - mTLS for internal
   - Certificate rotation

3. **Monitor and Log**
   - Flow logs
   - Traffic analysis
   - Anomaly detection

---

## Conclusion

Cross-cloud networking is critical for multi-cloud platforms. Design for security, performance, and reliability from the start.

Key Takeaways:
- Plan network architecture carefully
- Implement zero trust security
- Automate connectivity management
- Monitor continuously
- Optimize for performance