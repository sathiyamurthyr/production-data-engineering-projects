"""
adf_utils.py - Azure Data Factory Infrastructure Utilities & ARM Deployment Helpers
=====================================================================================
Production utilities for ARM template parameter generation, JSON validation, and deployment payloads.

Explanation:
    CI/CD pipelines for Azure Data Factory rely on Azure Resource Manager (ARM) templates
    exported from ADF development environments. This module provides Python utilities to:
    1. Parse and validate ARM template JSON structures.
    2. Generate environment-specific ARM parameter files (dev, staging, prod).
    3. Generate deployment parameters for Azure CLI (`az deployment group create`) or Azure Resource Management SDK.
    4. Override parameters dynamically (e.g. storage endpoints, Key Vault URIs).

Business Use Case:
    Automating multi-environment deployment (Dev -> Staging -> Prod) in GitHub Actions or Azure DevOps
    requires programmatically injecting environment parameters into ARM deployment manifests without manual edits.

Production Example:
    utils = ADFUtils()
    param_payload = utils.generate_arm_parameter_file(
        factory_name="adf-prod-eastus",
        key_vault_url="https://kv-prod.vault.azure.net/",
        adls_endpoint="https://adlsprod.dfs.core.windows.net/"
    )
    utils.save_json("configs/arm_params.prod.json", param_payload)

Interview Questions:
    Q: How do you implement CI/CD for Azure Data Factory across multiple environments?
    A: 1. Developers make changes in the ADF UI connected to a Git repository (dev branch).
       2. Merging to the collaboration branch triggers an automated build (ADF Utilities npm package)
          that generates ARM templates (`ARMTemplateForFactory.json`).
       3. The CI/CD pipeline deploys the ARM template to target environments (Staging/Prod) using
          environment-specific parameter files (`ARMTemplateParametersForFactory.json`).

    Q: What is the purpose of `arm-template-parameters-definition.json` in ADF Git integration?
    A: It allows customizing which properties in ADF resources are exposed as configurable ARM parameters
       during deployment (e.g. connection strings, warehouse names, core counts).
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ADFUtils:
    """
    Utility helper functions for ADF ARM templates, parameter file generation, and configuration processing.
    """

    @staticmethod
    def load_json(file_path: str) -> Dict[str, Any]:
        """
        Load and parse a JSON file.

        Args:
            file_path: File system path to JSON file

        Returns:
            Parsed JSON dictionary

        Raises:
            FileNotFoundError: If file does not exist
            json.JSONDecodeError: If JSON syntax is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.debug("Successfully loaded JSON from %s", file_path)
        return data

    @staticmethod
    def save_json(file_path: str, data: Dict[str, Any], indent: int = 2) -> None:
        """
        Save dictionary as formatted JSON file.

        Args:
            file_path: Output file path
            data: Dictionary payload
            indent: Indentation formatting spaces
        """
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

        logger.info("Saved JSON file: %s", file_path)

    @classmethod
    def generate_arm_parameter_file(
        cls,
        factory_name: str,
        key_vault_url: str,
        adls_endpoint: str,
        environment: str = "prod",
        additional_parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate standard ARM template parameters dictionary structure (`ARMTemplateParametersForFactory.json`).

        Args:
            factory_name: Target Data Factory instance name
            key_vault_url: Target Key Vault URL
            adls_endpoint: Target ADLS Gen2 DFS endpoint URL
            environment: Environment name ('dev', 'staging', 'prod')
            additional_parameters: Custom parameter overrides

        Returns:
            ARM parameter file structure dictionary
        """
        parameters: Dict[str, Any] = {
            "factoryName": {"value": factory_name},
            "KeyVaultLS_properties_typeProperties_baseUrl": {"value": key_vault_url},
            "ADLSGen2LS_properties_typeProperties_url": {"value": adls_endpoint},
            "environmentTag": {"value": environment},
        }

        if additional_parameters:
            for key, val in additional_parameters.items():
                parameters[key] = {"value": val}

        return {
            "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
            "contentVersion": "1.0.0.0",
            "parameters": parameters,
        }

    @classmethod
    def validate_arm_template_syntax(cls, arm_template_dict: Dict[str, Any]) -> List[str]:
        """
        Validate basic syntax constraints of an ARM template JSON structure.

        Args:
            arm_template_dict: ARM template content dictionary

        Returns:
            List of validation warning/error strings (empty list if clean)
        """
        errors = []

        if "$schema" not in arm_template_dict:
            errors.append("Missing required field '$schema' in ARM template.")
        if "contentVersion" not in arm_template_dict:
            errors.append("Missing required field 'contentVersion' in ARM template.")
        if "resources" not in arm_template_dict or not isinstance(arm_template_dict["resources"], list):
            errors.append("Missing or invalid 'resources' array in ARM template.")

        resources = arm_template_dict.get("resources", [])
        for i, res in enumerate(resources):
            if "type" not in res:
                errors.append(f"Resource index {i} is missing required field 'type'.")
            if "name" not in res:
                errors.append(f"Resource index {i} is missing required field 'name'.")

        return errors

    @classmethod
    def build_az_cli_deployment_command(
        cls,
        resource_group: str,
        template_file: str,
        parameters_file: str,
        deployment_name: Optional[str] = None,
    ) -> str:
        """
        Build Azure CLI command string for ARM template deployment.

        Args:
            resource_group: Target Azure Resource Group name
            template_file: Path to ARM template file
            parameters_file: Path to ARM parameters file
            deployment_name: Deployment run name

        Returns:
            Azure CLI command string ready to execute
        """
        name_part = f" --name {deployment_name}" if deployment_name else ""
        return (
            f"az deployment group create"
            f" --resource-group {resource_group}"
            f" --template-file {template_file}"
            f" --parameters {parameters_file}"
            f"{name_part}"
        )
