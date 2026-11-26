"""
Azure Databricks Enterprise Security Patterns & Network Isolation
===================================================================
Production security configurations for Azure Databricks including VNet Injection,
Private Endpoints, Secure Cluster Connectivity (No Public IP), and AAD RBAC integration.

Business Use Case:
    Highly regulated industries (Banking, Healthcare, Defense) mandate strict network isolation.
    Azure Databricks workspaces must be deployed inside customer-managed virtual networks (VNet Injection)
    with public access disabled, utilizing Private Endpoints for storage and Key Vault access,
    and delegating user authentication to Azure Active Directory (Microsoft Entra ID) with RBAC.

Architecture:
    Customer VNet (10.178.0.0/16)
    ├── Public Subnet  (10.178.0.0/24)  ── Network Intent Policy for Databricks Host
    ├── Private Subnet (10.178.1.0/24)  ── Network Intent Policy for Databricks Container
    └── Transit Subnet (10.178.2.0/24)
        ├── Private Endpoint: ADLS Gen2 (dfs.core.windows.net)
        ├── Private Endpoint: Key Vault (vault.azure.net)
        ├── Private Endpoint: Databricks Control Plane (front-end / web-app)
        └── Private Endpoint: Databricks Relay (back-end SCC)

Security Pillars:
    1. VNet Injection: Control IP space, NSGs, and user-defined routes (UDR).
    2. No Public IP (NPIP): Public IP addresses are not created for cluster nodes.
    3. Private Link: Exclude public internet routing for control plane and storage traffic.
    4. Encryption: Managed Services & Storage encryption with Customer-Managed Keys (CMK).
    5. Access Control: Azure AD single sign-on, conditional access, and SCIM user provisioning.

Interview Questions:
    Q: What is VNet Injection in Azure Databricks and why is it used?
    A: VNet Injection deploys Azure Databricks cluster nodes into your own existing Azure VNet
       rather than an Azure-managed VNet. This allows custom Network Security Groups (NSGs),
       user-defined routing (UDR) via Azure Firewall, and private connectivity to on-premise networks.

    Q: What is Secure Cluster Connectivity (SCC) / No Public IP mode?
    A: SCC ensures that cluster VMs in the private VNet do not have public IP addresses.
       Nodes initiate outbound connections to the Databricks Control Plane relay using secure tunnels,
       eliminating inbound public internet exposure.

    Q: How do Private Endpoints secure ADLS Gen2 access from Databricks?
    A: Private Endpoints map ADLS Gen2 storage accounts to private IP addresses within the VNet.
       Databricks nodes communicate with ADLS over Azure internal backbone network, allowing storage
       firewalls to block all public internet traffic.
"""

import logging
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AzureSecurityPatterns")


class AzureSecurityPatternsManager:
    """
    Manager for generating and verifying Azure Databricks security, network isolation,
    and RBAC topology templates.
    """

    def __init__(self, resource_group: str = "rg-databricks-prod-eastus", location: str = "eastus"):
        self.resource_group = resource_group
        self.location = location

    def generate_vnet_injection_arm_template(
        self,
        vnet_name: str = "vnet-databricks-prod",
        address_prefix: str = "10.178.0.0/16",
        public_subnet_prefix: str = "10.178.0.0/24",
        private_subnet_prefix: str = "10.178.1.0/24"
    ) -> Dict[str, Any]:
        """
        Generate ARM/Bicep network deployment configuration for VNet Injected Azure Databricks Workspace.
        """
        config = {
            "vnet": {
                "name": vnet_name,
                "addressPrefix": address_prefix,
                "subnets": [
                    {
                        "name": "subnet-databricks-public",
                        "addressPrefix": public_subnet_prefix,
                        "delegations": [{
                            "name": "databricks-del-public",
                            "serviceName": "Microsoft.Databricks/workspaces"
                        }]
                    },
                    {
                        "name": "subnet-databricks-private",
                        "addressPrefix": private_subnet_prefix,
                        "delegations": [{
                            "name": "databricks-del-private",
                            "serviceName": "Microsoft.Databricks/workspaces"
                        }]
                    }
                ]
            },
            "workspace_security": {
                "enableNoPublicIp": True,
                "requireInfrastructureEncryption": True,
                "publicNetworkAccess": "Disabled"
            }
        }
        logger.info(f"Generated VNet Injection topology for VNet '{vnet_name}' with No Public IP enabled.")
        return config

    def generate_private_endpoint_config(
        self,
        target_resource_id: str,
        target_subresource: str = "dfs",
        subnet_id: str = "/subscriptions/sub-id/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/vnet/subnets/subnet-endpoints"
    ) -> Dict[str, Any]:
        """
        Generate Private Endpoint configuration for securing ADLS Gen2 or Key Vault connectivity.
        """
        pe_config = {
            "name": f"pe-{target_subresource}-databricks",
            "location": self.location,
            "properties": {
                "subnet": {"id": subnet_id},
                "privateLinkServiceConnections": [
                    {
                        "name": f"plsc-{target_subresource}",
                        "properties": {
                            "privateLinkServiceId": target_resource_id,
                            "groupIds": [target_subresource]
                        }
                    }
                ]
            }
        }
        logger.info(f"Generated Private Endpoint spec for subresource '{target_subresource}'")
        return pe_config

    @staticmethod
    def get_security_rbac_matrix() -> List[Dict[str, str]]:
        """
        Returns Databricks Azure AD RBAC role permission mapping matrix for governance documentation.
        """
        return [
            {
                "Azure Role": "Contributor",
                "Scope": "Databricks Workspace Resource Group",
                "Databricks Role": "Workspace Admin",
                "Description": "Manages ARM deployment, clusters, VNet settings, and secret scopes."
            },
            {
                "Azure Role": "Reader",
                "Scope": "Databricks Workspace Resource Group",
                "Databricks Role": "Data Engineer / User",
                "Description": "Can launch jobs and write code; cannot alter infrastructure or network NSGs."
            },
            {
                "Azure Role": "Storage Blob Data Contributor",
                "Scope": "ADLS Gen2 Storage Account",
                "Databricks Role": "Access Connector Managed Identity",
                "Description": "Grants Unity Catalog metastore read/write permissions on data lake paths."
            },
            {
                "Azure Role": "Key Vault Secrets User",
                "Scope": "Azure Key Vault",
                "Databricks Role": "Databricks First-Party App Service Principal",
                "Description": "Allows Databricks secret scopes to read secrets without storing KV keys in workspace."
            }
        ]


if __name__ == "__main__":
    sec_mgr = AzureSecurityPatternsManager()
    vnet_spec = sec_mgr.generate_vnet_injection_arm_template()
    rbac_matrix = sec_mgr.get_security_rbac_matrix()
    print("VNet Spec Sample:", vnet_spec["workspace_security"])
    print(f"RBAC Roles Configured: {len(rbac_matrix)}")
