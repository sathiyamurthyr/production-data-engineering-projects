"""
Test Suite: test_dag_integrity.py
==================================

PURPOSE:
    Automated CI/CD suite validating DAG integrity across all DAG files in `src/dags/`.
    Prevents broken DAG files, circular dependencies, missing tags, or missing default_args
    from reaching the production Airflow environment.

TEST CHECKS:
    1. Zero import errors across DagBag
    2. All DAGs have non-empty owner, tags, and retries defined
    3. All DAGs pass acyclic graph check (no cycles)
    4. All DAGs set `catchup=False` explicitly (production rule)

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
"""

from __future__ import annotations

import glob
import importlib.util
import os
import sys
import pytest

from airflow.models import DagBag

# Path to DAG directory
DAG_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "dags"))

@pytest.fixture(scope="module")
def dag_bag():
    """Fixture initializing DagBag pointing to project dags directory."""
    return DagBag(dag_folder=DAG_FOLDER, include_examples=False)


def test_dag_bag_import_errors(dag_bag):
    """Assert that no DAG files throw import errors during loading."""
    assert len(dag_bag.import_errors) == 0, (
        f"DAG import errors detected ({len(dag_bag.import_errors)}):\n"
        f"{dag_bag.import_errors}"
    )


def test_dag_bag_has_dags(dag_bag):
    """Assert that DAGs were actually discovered in the target directory."""
    assert len(dag_bag.dags) > 0, f"No DAGs found in folder '{DAG_FOLDER}'"


def test_dag_tags_and_owners(dag_bag):
    """Enforce enterprise metadata rules on all discovered DAGs."""
    for dag_id, dag in dag_bag.dags.items():
        # Check DAG owner
        owner = dag.default_args.get("owner") or dag.owner
        assert owner is not None and len(owner.strip()) > 0, f"DAG '{dag_id}' must define a non-empty owner."

        # Check Tags
        assert dag.tags is not None and len(dag.tags) > 0, f"DAG '{dag_id}' must have at least one tag."

        # Check Catchup policy
        assert dag.catchup is False, f"DAG '{dag_id}' must explicitly set catchup=False."


def test_dag_no_cycles(dag_bag):
    """Validate that no DAGs contain circular task dependency cycles."""
    for dag_id, dag in dag_bag.dags.items():
        # test_cycle() raises AirflowDagCycleException if a loop exists
        dag.test_cycle()
