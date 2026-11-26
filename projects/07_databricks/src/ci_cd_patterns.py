"""
Module 15: Databricks Asset Bundles (DABs) & CI/CD Deployment Patterns
======================================================================

Explanation:
    Databricks Asset Bundles (DABs) provide Infra-as-Code (IaC) capabilities for Databricks.
    They allow defining workspace artifacts, Delta Live Tables pipelines, Databricks Jobs,
    and cluster resources as declarative YAML files (`databricks.yml`) with environment targeting.

Business Use Case:
    - Automating CI/CD pipelines across Dev, Staging, and Production environments via GitHub Actions / Azure DevOps.
    - Software engineering best practices: version controlling jobs, DLT pipelines, notebooks, and cluster configs.
    - Multi-workspace deployment management without manually clicking in the Databricks UI.
    - Enabling pull request validation (`databricks bundle validate`) before merging code to main branch.

Architecture:
    Git Repository (Source Code + `databricks.yml`)
                         |
           GitHub Actions / Azure DevOps Pipeline
                         |
       +---------------------------------------------------+
       | 1. databricks bundle validate -t dev              |
       | 2. pytest tests/                                  |
       | 3. databricks bundle deploy -t prod               |
       +---------------------------------------------------+
                         |
      +------------------------------------------------------+
      |              Databricks Workspace Targets            |
      |  +--------------------+      +--------------------+  |
      |  | Dev Workspace      |      | Prod Workspace     |  |
      |  | (databricks-dev)   |      | (databricks-prod)  |  |
      |  +--------------------+      +--------------------+  |
      +------------------------------------------------------+

Performance Notes:
    - DABs deploy code directly to workspace Repos or DBFS volume paths atomically.
    - Variable substitution (`${var.catalog_name}`) ensures environment-specific resource bindings.

Common Mistakes:
    - Hardcoding workspace URLs or tokens in `databricks.yml` (use environment variables or profile bindings).
    - Deploying production jobs directly from developer workstations instead of authorized CI/CD service principals.
    - Forgetting to lock target environment configurations, leading to accidental overwrites of prod jobs from dev branch.

Interview Questions:
    Q: What are Databricks Asset Bundles (DABs) and why are they replacing legacy deployment tools?
    A: DABs are Databricks' official Infra-as-Code tool. They simplify multi-environment deployments by combining
       job DAG definitions, DLT pipelines, and source code into unified YAML bundles with built-in CI/CD commands.

    Q: How do you separate Dev, Staging, and Production deployment targets in a `databricks.yml` bundle?
    A: Using the `targets` block in `databricks.yml`. Each target defines specific workspace hosts, default cluster tags,
       Unity Catalog names, and permission overrides.
"""

import logging
import yaml
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DatabricksAssetBundleGenerator:
    """
    Generator and builder for Databricks Asset Bundles (DABs) `databricks.yml` specs
    and CI/CD GitHub Actions deployment workflow manifests.
    """

    def __init__(self, bundle_name: str = "production_data_engineering"):
        self.bundle_name = bundle_name

    def generate_databricks_yml(
        self,
        dev_host: str = "https://dev.cloud.databricks.com",
        prod_host: str = "https://prod.cloud.databricks.com",
    ) -> str:
        """
        Generates standard Databricks Asset Bundle YAML structure.
        """
        bundle_spec = {
            "bundle": {
                "name": self.bundle_name,
            },
            "include": [
                "resources/*.yml",
            ],
            "targets": {
                "dev": {
                    "mode": "development",
                    "default": True,
                    "workspace": {
                        "host": dev_host,
                    },
                    "variables": {
                        "catalog": "dev_catalog",
                        "environment": "dev",
                    },
                },
                "prod": {
                    "mode": "production",
                    "workspace": {
                        "host": prod_host,
                    },
                    "variables": {
                        "catalog": "prod_catalog",
                        "environment": "prod",
                    },
                    "run_as": {
                        "service_principal_name": "sp_data_eng_prod",
                    },
                },
            },
            "variables": {
                "catalog": {
                    "description": "Unity Catalog target name",
                    "default": "dev_catalog",
                },
                "environment": {
                    "description": "Target deployment environment",
                    "default": "dev",
                },
            },
        }

        yaml_content = yaml.dump(bundle_spec, sort_keys=False, default_flow_style=False)
        logger.info(f"Generated databricks.yml manifest for bundle '{self.bundle_name}'")
        return yaml_content

    def generate_github_actions_workflow(self) -> str:
        """
        Generates production GitHub Actions workflow YAML for automated DAB deployment.
        """
        workflow = """
name: Databricks Asset Bundle CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    name: Validate Bundle & Run Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3

      - name: Set up Python 3.10
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install Dependencies & Databricks CLI
        run: |
          pip install pytest pytest-cov
          curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

      - name: Run Unit Tests
        run: |
          pytest tests/ --doctest-modules --junitxml=junit/test-results.xml

      - name: Validate Databricks Bundle
        env:
          DATABRICKS_HOST: ${{ secrets.DEV_DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DEV_DATABRICKS_TOKEN }}
        run: |
          databricks bundle validate -t dev

  deploy_prod:
    name: Deploy to Production Workspace
    needs: validate
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3

      - name: Install Databricks CLI
        run: |
          curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

      - name: Deploy Asset Bundle to Prod
        env:
          DATABRICKS_HOST: ${{ secrets.PROD_DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.PROD_DATABRICKS_TOKEN }}
        run: |
          databricks bundle deploy -t prod
""".strip()
        return workflow


if __name__ == "__main__":
    generator = DatabricksAssetBundleGenerator("lakehouse_etl_bundle")

    print("=== databricks.yml Bundle Configuration ===")
    print(generator.generate_databricks_yml())

    print("\n=== .github/workflows/deploy.yml GitHub Action Manifest ===")
    print(generator.generate_github_actions_workflow())
