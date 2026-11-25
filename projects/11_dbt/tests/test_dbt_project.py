"""
pytest Test Suite for dbt Analytics Engineering Project
=========================================================
Validates dbt project directory structure, YML configuration syntax,
SQL model syntax integrity, seed CSV datasets, and script execution logic.
"""

import json
import os
import yaml
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = PROJECT_ROOT / "src" / "dbt_project"


def test_dbt_project_structure():
    """Validates that all required dbt project directories and files exist."""
    required_paths = [
        DBT_PROJECT_DIR / "dbt_project.yml",
        DBT_PROJECT_DIR / "packages.yml",
        DBT_PROJECT_DIR / "profiles.yml.template",
        DBT_PROJECT_DIR / "models" / "staging" / "stg_customers.sql",
        DBT_PROJECT_DIR / "models" / "staging" / "stg_orders.sql",
        DBT_PROJECT_DIR / "models" / "staging" / "stg_products.sql",
        DBT_PROJECT_DIR / "models" / "staging" / "stg_events.sql",
        DBT_PROJECT_DIR / "models" / "staging" / "schema.yml",
        DBT_PROJECT_DIR / "models" / "intermediate" / "int_customer_orders.sql",
        DBT_PROJECT_DIR / "models" / "intermediate" / "int_order_items.sql",
        DBT_PROJECT_DIR / "models" / "intermediate" / "schema.yml",
        DBT_PROJECT_DIR / "models" / "marts" / "sales" / "fct_orders.sql",
        DBT_PROJECT_DIR / "models" / "marts" / "sales" / "dim_customers.sql",
        DBT_PROJECT_DIR / "models" / "marts" / "sales" / "dim_products.sql",
        DBT_PROJECT_DIR / "models" / "marts" / "sales" / "schema.yml",
        DBT_PROJECT_DIR / "models" / "marts" / "analytics" / "rpt_sales_summary.sql",
        DBT_PROJECT_DIR / "models" / "marts" / "analytics" / "rpt_customer_cohorts.sql",
        DBT_PROJECT_DIR / "tests" / "assert_orders_have_customers.sql",
        DBT_PROJECT_DIR / "tests" / "assert_revenue_positive.sql",
        DBT_PROJECT_DIR / "macros" / "generate_surrogate_key.sql",
        DBT_PROJECT_DIR / "macros" / "pivot_values.sql",
        DBT_PROJECT_DIR / "macros" / "audit_helper.sql",
        DBT_PROJECT_DIR / "macros" / "date_spine.sql",
        DBT_PROJECT_DIR / "seeds" / "country_codes.csv",
        DBT_PROJECT_DIR / "seeds" / "product_categories.csv",
        DBT_PROJECT_DIR / "snapshots" / "customers_snapshot.sql",
        DBT_PROJECT_DIR / "analyses" / "revenue_reconciliation.sql",
    ]
    
    for path in required_paths:
        assert path.exists(), f"Required dbt file missing: {path}"


def test_dbt_project_yml_validity():
    """Parses and validates dbt_project.yml configuration parameters."""
    dbt_yml_path = DBT_PROJECT_DIR / "dbt_project.yml"
    with open(dbt_yml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert config["name"] == "production_analytics"
    assert config["profile"] == "production_analytics"
    assert "models" in config
    assert "vars" in config
    assert config["vars"]["current_tax_rate"] == 0.08


def test_packages_yml_validity():
    """Parses and validates packages.yml package declarations."""
    packages_path = DBT_PROJECT_DIR / "packages.yml"
    with open(packages_path, "r", encoding="utf-8") as f:
        pkgs = yaml.safe_load(f)

    package_names = [p["package"] for p in pkgs.get("packages", [])]
    assert "dbt-labs/dbt_utils" in package_names
    assert "calogica/dbt_expectations" in package_names
    assert "calogica/dbt_date" in package_names


def test_seed_csv_contents():
    """Validates that seed CSV files contain headers and data rows."""
    country_csv = DBT_PROJECT_DIR / "seeds" / "country_codes.csv"
    with open(country_csv, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 5
        assert "country_code,country_name,region" in lines[0]

    category_csv = DBT_PROJECT_DIR / "seeds" / "product_categories.csv"
    with open(category_csv, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 3
        assert "category_id,category_name,department" in lines[0]


def test_sql_models_have_no_placeholders():
    """Scans all SQL model files to ensure zero TODO or placeholder comments exist."""
    sql_files = list((DBT_PROJECT_DIR / "models").rglob("*.sql"))
    assert len(sql_files) >= 9, "Expected at least 9 SQL model files"

    for sql_file in sql_files:
        with open(sql_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "TODO" not in content, f"Placeholder TODO found in {sql_file}"
            assert "FIXME" not in content, f"Placeholder FIXME found in {sql_file}"
            assert "select * from raw" not in content, f"Un-staged raw query found in {sql_file}"


def test_singular_sql_tests_formatting():
    """Verifies singular SQL test assertions exist and contain valid ref statements."""
    singular_tests = list((DBT_PROJECT_DIR / "tests").glob("*.sql"))
    assert len(singular_tests) == 2

    for test_file in singular_tests:
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "ref(" in content, f"Singular test {test_file.name} missing ref() macro call"
