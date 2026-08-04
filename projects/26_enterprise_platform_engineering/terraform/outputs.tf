"""
Terraform Outputs
Enterprise Platform Engineering Infrastructure
"""

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.platform_rg.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.platform_rg.location
}

output "kubernetes_cluster_name" {
  description = "Name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.platform_aks.name
}

output "kubernetes_cluster_host" {
  description = "AKS cluster host"
  value       = azurerm_kubernetes_cluster.platform_aks.kube_config[0].host
  sensitive   = true
}

output "kubernetes_cluster_ca_certificate" {
  description = "AKS cluster CA certificate"
  value       = azurerm_kubernetes_cluster.platform_aks.kube_config[0].cluster_ca_certificate
  sensitive   = true
}

output "postgresql_server_name" {
  description = "PostgreSQL server name"
  value       = azurerm_postgresql_flexible_server.platform_db.name
}

output "postgresql_server_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.platform_db.fqdn
}

output "postgresql_database_name" {
  description = "PostgreSQL database name"
  value       = azurerm_postgresql_flexible_server_database.platform_db.name
}

output "postgresql_administrator_login" {
  description = "PostgreSQL administrator login"
  value       = azurerm_postgresql_flexible_server.platform_db.administrator_login
  sensitive   = true
}

output "postgresql_administrator_password" {
  description = "PostgreSQL administrator password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.platform_vault.name
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.platform_vault.vault_uri
}

output "redis_cache_name" {
  description = "Redis cache name"
  value       = azurerm_redis_cache.platform_cache.name
}

output "redis_cache_host" {
  description = "Redis cache host"
  value       = azurerm_redis_cache.platform_cache.hostname
}

output "redis_cache_port" {
  description = "Redis cache port"
  value       = azurerm_redis_cache.platform_cache.ssl_port
}

output "container_registry_name" {
  description = "Container registry name"
  value       = azurerm_container_registry.platform_acr.name
}

output "container_registry_login_server" {
  description = "Container registry login server"
  value       = azurerm_container_registry.platform_acr.login_server
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.platform_workspace.id
}

output "virtual_network_name" {
  description = "Virtual network name"
  value       = azurerm_virtual_network.platform_vnet.name
}

output "subnet_name" {
  description = "Subnet name"
  value       = azurerm_subnet.platform_subnet.name
}

output "aks_identity_client_id" {
  description = "AKS managed identity client ID"
  value       = azurerm_user_assigned_identity.aks_identity.client_id
  sensitive   = true
}

output "platform_services_connection_string" {
  description = "Database connection string for platform services"
  value       = "postgresql://${azurerm_postgresql_flexible_server.platform_db.administrator_login}:${random_password.db_password.result}@${azurerm_postgresql_flexible_server.platform_db.fqdn}:5432/${azurerm_postgresql_flexible_server_database.platform_db.name}?sslmode=require"
  sensitive   = true
}

output "platform_api_endpoint" {
  description = "Platform API endpoint"
  value       = "https://${azurerm_kubernetes_cluster.platform_aks.kube_config[0].host}/api/v1"
  sensitive   = true
}

# Cost Management Outputs
output "estimated_monthly_cost" {
  description = "Estimated monthly cost in USD"
  value = {
    aks_cluster    = 450
    postgresql     = 120
    redis_cache    = 150
    key_vault      = 25
    container_registry = 50
    networking     = 50
    total          = 845
  }
}