"""
Azure DevOps CI/CD Automation & Databricks Asset Bundles (DABs)
==============================================================
Production patterns for CI/CD automation of Azure Databricks code, notebooks,
and Delta Live Tables using Azure DevOps Pipelines and Databricks CLI v2.

Business Use Case:
    Enterprise software engineering practices require automated testing, linting, code packaging,
    and zero-downtime deployment across multi-stage environments (Development, Staging, Production).
    Changes committed to Git must be validated by unit tests, packaged into Python wheels,
    and deployed to Databricks workspaces using Azure DevOps pipeline agents and Service Principal authentication.

Architecture:
    Azure Repos / GitHub (Git Flow)
        │ (Pull Request / Merge to main)
        ▼
    Azure DevOps CI Pipeline (`azure_devops_pipeline.yml`)
        ├── 1. Lint & Static Analysis (flake8, black, mypy)
        ├── 2. Execute PyTest Unit Tests (with mock Spark / local PySpark)
        ├── 3. Package Source Code into Python Wheel (.whl)
        └── 4. Publish Artifacts to Azure DevOps Artifacts Registry
        │
        ▼
    Azure DevOps CD Release Pipeline
        ├── 1. Deploy Wheel & Databricks Asset Bundles (DABs) to Dev Workspace
        ├── 2. Execute Integration & Smoke Tests in Dev
        ├── 3. Approval Gate (Senior Lead / Data Governance Approval)
        └── 4. Deploy Bundle & Update Job Schedules in Production Workspace

Key Deployment Frameworks:
    - Databricks Asset Bundles (DABs): Declarative YAML bundle infrastructure (`databricks.yml`).
    - Databricks REST API / CLI v2: Programmatic cluster, secret, and job management.
    - Databricks Repo API: Sync git repositories directly to workspace user directories.

Interview Questions:
    Q: What are Databricks Asset Bundles (DABs) and how do they improve CI/CD?
    A: DABs are a software engineering framework that allows developers to define Databricks projects
       (jobs, pipelines, notebooks, libraries) as code in YAML configuration files. DABs manage build,
       validation, and deployment targeting multiple workspaces (dev, stage, prod) cleanly without custom shell scripts.

    Q: How do you authenticate Azure DevOps agents to Azure Databricks securely?
    A: Use Azure Active Directory (Microsoft Entra ID) Service Principal authentication.
       The Azure DevOps Service Connection passes Azure SP OAuth credentials (`AZURE_CLIENT_ID`,
       `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`) to the Databricks CLI environment variables.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DevOpsIntegrationManager")


class DevOpsIntegrationManager:
    """
    Manager for orchestrating Azure DevOps CI/CD deployment definitions,
    Databricks Asset Bundle (DAB) specs, and deployment validation scripts.
    """

    def __init__(self, project_name: str = "14_azure_databricks"):
        self.project_name = project_name

    def generate_databricks_asset_bundle_yaml(self) -> str:
        """
        Generate declarative `databricks.yml` asset bundle definition.
        """
        bundle_yaml = f"""# Databricks Asset Bundle Configuration
bundle:
  name: {self.project_name}

include:
  - resources/*.yml

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://adb-dev-123456789.azuredatabricks.net
      root_path: /Shared/bundles/dev/{self.project_name}

  staging:
    mode: staging
    workspace:
      host: https://adb-staging-123456789.azuredatabricks.net
      root_path: /Shared/bundles/staging/{self.project_name}

  prod:
    mode: production
    workspace:
      host: https://adb-prod-123456789.azuredatabricks.net
      root_path: /Shared/bundles/prod/{self.project_name}
    run_as:
      service_principal_name: sp-databricks-prod-cicd

resources:
  jobs:
    medallion_etl_job:
      name: "[${{bundle.target}}] Azure Databricks Medallion ETL Job"
      tasks:
        - task_key: run_etl_pipeline
          job_cluster_key: etl_cluster
          spark_python_task:
            python_file: src/azure_etl_pipeline.py
            parameters:
              - "--env"
              - "${{bundle.target}}"
      job_clusters:
        - job_cluster_key: etl_cluster
          new_cluster:
            spark_version: 14.3.x-scala2.12
            node_type_id: Standard_D4ds_v5
            num_workers: 2
            autotermination_minutes: 20
"""
        logger.info("Generated Databricks Asset Bundle YAML spec.")
        return bundle_yaml

    def generate_azure_devops_pipeline_yaml(self) -> str:
        """
        Generate Azure DevOps pipeline configuration file (`azure_devops_pipeline.yml`).
        """
        pipeline_yaml = """# Azure DevOps CI/CD Pipeline for Azure Databricks
trigger:
  branches:
    include:
      - main
      - release/*

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: Databricks-Prod-Secrets

stages:
  - stage: Build_And_Test
    displayName: 'Lint, Test & Package'
    jobs:
      - job: CI_Job
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
            displayName: 'Set Python Version'

          - script: |
              python -m pip install --upgrade pip
              pip install pytest pytest-cov flake8 setuptools wheel
              pip install -r requirements.txt
            displayName: 'Install Dependencies'

          - script: |
              flake8 src/ --max-line-length=120
            displayName: 'Code Quality Check'

          - script: |
              pytest tests/ --doctest-modules --junitxml=junit/test-results.xml --cov=src
            displayName: 'Run PyTest Unit Tests'

          - task: PublishTestResults@2
            condition: succeededOrFailed()
            inputs:
              testResultsFiles: '**/test-*.xml'
              testRunTitle: 'PyTest Execution Results'

  - stage: Deploy_To_Production
    displayName: 'Deploy to Azure Databricks Prod'
    dependsOn: Build_And_Test
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: CD_Job
        environment: 'Databricks-Production'
        strategy:
          runOnce:
            deploy:
              steps:
                - script: |
                    curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
                  displayName: 'Install Databricks CLI v2'

                - script: |
                    databricks bundle deploy --target prod
                  env:
                    DATABRICKS_HOST: $(DATABRICKS_HOST)
                    DATABRICKS_CLIENT_ID: $(AZURE_CLIENT_ID)
                    DATABRICKS_CLIENT_SECRET: $(AZURE_CLIENT_SECRET)
                    DATABRICKS_AZURE_TENANT_ID: $(AZURE_TENANT_ID)
                  displayName: 'Deploy Databricks Asset Bundle to Production'
"""
        logger.info("Generated Azure DevOps Pipeline YAML definition.")
        return pipeline_yaml


if __name__ == "__main__":
    devops_mgr = DevOpsIntegrationManager()
    dab_spec = devops_mgr.generate_databricks_asset_bundle_yaml()
    devops_spec = devops_mgr.generate_azure_devops_pipeline_yaml()
    print("DAB Spec Sample Line Count:", len(dab_spec.splitlines()))
    print("DevOps Spec Sample Line Count:", len(devops_spec.splitlines()))
