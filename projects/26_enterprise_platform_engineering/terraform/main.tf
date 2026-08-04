"""
Terraform Configuration
Enterprise Platform Engineering Infrastructure
"""

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.20"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend configuration for state management
  backend "azurerm" {
    resource_group_name  = "platform-terraform-rg"
    storage_account_name = "platformtfstate"
    container_name       = "tfstate"
    key                  = "enterprise-platform.terraform.tfstate"
  }
}

# Configure Azure provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!@#$%^&*()"
}

# Resource Group
resource "azurerm_resource_group" "platform_rg" {
  name     = "enterprise-platform-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "Enterprise Platform"
    ManagedBy   = "Terraform"
  }
}

# Virtual Network
resource "azurerm_virtual_network" "platform_vnet" {
  name                = "platform-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.platform_rg.location
  resource_group_name = azurerm_resource_group.platform_rg.name

  tags = {
    Environment = var.environment
  }
}

# Subnets
resource "azurerm_subnet" "platform_subnet" {
  name                 = "platform-subnet"
  resource_group_name  = azurerm_resource_group.platform_rg.name
  virtual_network_name = azurerm_virtual_network.platform_vnet.name
  address_prefixes     = ["10.0.1.0/24"]

  # Delegate to AKS
  delegation {
    name = "aks-delegation"
    service_delegation {
      name    = "Microsoft.ContainerService/managedClusters"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "platform_aks" {
  name                = "platform-aks-${var.environment}"
  location            = azurerm_resource_group.platform_rg.location
  resource_group_name = azurerm_resource_group.platform_rg.name
  dns_prefix          = "platform-aks"
  kubernetes_version  = var.kubernetes_version

  # Default node pool
  default_node_pool {
    name                = "systempool"
    node_count          = var.system_node_count
    vm_size             = var.system_node_vm_size
    vnet_subnet_id      = azurerm_subnet.platform_subnet.id
    zones               = ["1", "2", "3"]
    enable_auto_scaling = true
    min_count           = 1
    max_count           = 5

    node_labels = {
      role = "system"
    }

    node_taints = [
      "CriticalAddonsOnly=true:NoSchedule"
    ]
  }

  # User node pool for workloads
  node_pool {
    name                = "userpool"
    node_count          = var.user_node_count
    vm_size             = var.user_node_vm_size
    vnet_subnet_id      = azurerm_subnet.platform_subnet.id
    zones               = ["1", "2", "3"]
    enable_auto_scaling = true
    min_count           = 3
    max_count           = 20

    node_labels = {
      role = "user"
    }

    # Enable node autoprovisioning
    auto_scaling_profile {
      balance_similar_node_groups      = true
      expander                          = "least-waste"
      max_node_provisioning_time        = "15m"
      max_unschedulable_pods            = 25
      new_pod_scale_up_delay            = "10s"
      scale_down_delay_after_add        = "10m"
      scale_down_unneeded_time          = "10m"
      scale_down_unready_time           = "20m"
      scan_interval                     = "10s"
    }
  }

  # Identity
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks_identity.id]
  }

  # Network profile
  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    dns_service_ip    = "10.0.10.10"
    docker_bridge_cidr = "172.17.0.1/16"
    service_cidr      = "10.0.10.0/24"
  }

  # Add-ons
  addon_profile {
    kube_dashboard {
      enabled = true
    }

    azure_policy {
      enabled = true
    }

    oms_agent {
      enabled = true
      log_analytics_workspace_id = azurerm_log_analytics_workspace.platform_workspace.id
    }

    # Enable monitoring
    azure_policy {
      enabled = true
    }
  }

  # RBAC
  role_based_access_control {
    enabled = true

    azure_active_directory_role_based_access_control {
      managed                = true
      azure_rbac_enabled     = true
      tenant_id              = data.azurerm_client_config.current.tenant_id
    }
  }

  tags = {
    Environment = var.environment
    Project     = "Enterprise Platform"
  }
}

# User Assigned Identity for AKS
resource "azurerm_user_assigned_identity" "aks_identity" {
  name                = "platform-aks-identity"
  resource_group_name = azurerm_resource_group.platform_rg.name
  location            = azurerm_resource_group.platform_rg.location
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "platform_workspace" {
  name                = "platform-logs-${var.environment}"
  location            = azurerm_resource_group.platform_rg.location
  resource_group_name = azurerm_resource_group.platform_rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
  }
}

# PostgreSQL Server
resource "azurerm_postgresql_flexible_server" "platform_db" {
  name                   = "platform-postgres-${var.environment}"
  resource_group_name    = azurerm_resource_group.platform_rg.name
  location               = azurerm_resource_group.platform_rg.location
  version                = "14"
  delegated_subnet_id    = azurerm_subnet.platform_subnet.id
  private_dns_zone_id    = azurerm_private_dns_zone.postgres_dns.id

  administrator_login          = "platformadmin"
  administrator_password        = random_password.db_password.result
  storage_mb                   = 32768
  sku_name                     = "B_Standard_B4ms"
  backup_retention_days        = 7
  geo_redundant_backup_enabled = var.environment == "prod" ? true : false

  # High availability for production
  high_availability {
    mode = "ZoneRedundant"
  }

  # Maintenance window
  maintenance_window {
    day_of_week  = 0  # Sunday
    start_hour   = 2
    start_minute = 0
  }

  tags = {
    Environment = var.environment
  }
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "platform_db" {
  name      = "platform"
  server_id = azurerm_postgresql_flexible_server.platform_db.id

  charset   = "UTF8"
  collation = "en_US.UTF8"
}

# PostgreSQL Firewall Rule - Allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name                = "AllowAzureServices"
  server_id           = azurerm_postgresql_flexible_server.platform_db.id
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgres_dns" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.platform_rg.name
}

# Key Vault
resource "azurerm_key_vault" "platform_vault" {
  name                = "platform-vault-${var.environment}"
  location            = azurerm_resource_group.platform_rg.location
  resource_group_name = azurerm_resource_group.platform_rg.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "premium"

  # Enable purge protection for production
  purge_protection_enabled = var.environment == "prod" ? true : false
  soft_delete_retention_days = 90

  # Access policies
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get",
      "List",
      "Create",
      "Delete",
      "Update",
      "Encrypt",
      "Decrypt"
    ]

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Purge"
    ]
  }

  tags = {
    Environment = var.environment
  }
}

# Redis Cache
resource "azurerm_redis_cache" "platform_cache" {
  name                = "platform-redis-${var.environment}"
  location            = azurerm_resource_group.platform_rg.location
  resource_group_name = azurerm_resource_group.platform_rg.name
  capacity            = 2
  family              = "P"
  sku_name            = "Premium"
  enable_non_ssl_port = false

  # Enable data persistence
  rdb_backup_enabled = true
  rdb_backup_frequency = 3600  # 1 hour
  rdb_backup_max_snapshot_count = 1

  # Redis configuration
  redis_configuration {
    "maxmemory-reserved" = 50
    "maxmemory-delta"    = 50
    "maxmemory-policy"   = "allkeys-lru"
  }

  # Enable firewall
  public_network_access_enabled = true

  tags = {
    Environment = var.environment
  }
}

# Container Registry
resource "azurerm_container_registry" "platform_acr" {
  name                = "platformacr${var.environment}"
  resource_group_name = azurerm_resource_group.platform_rg.name
  location            = azurerm_resource_group.platform_rg.location
  sku                 = "Premium"
  admin_enabled       = true

  # Enable security features
  retention_policy {
    count    = 30
    days     = 30
  }

  trust_policy {
    enabled = true
  }

  export_policy {
    enabled = false
  }

  tags = {
    Environment = var.environment
  }
}

# Assign ACR Pull role to AKS
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = azurerm_container_registry.platform_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.platform_aks.kubelet_identity[0].object_id
}

# Storage Account for Terraform state
resource "azurerm_storage_account" "tfstate" {
  name                     = "platformtfstate${var.environment}"
  resource_group_name      = azurerm_resource_group.platform_rg.name
  location                 = azurerm_resource_group.platform_rg.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # Enable versioning
  blob_versioning_enabled = true

  # Enable soft delete
  delete_retention_policy {
    days = 90
  }

  # Container for terraform state
  container {
    name                  = "tfstate"
    container_access_type = "private"
  }

  tags = {
    Environment = var.environment
  }
}