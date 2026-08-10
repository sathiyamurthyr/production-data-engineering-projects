"""Root conftest.py for enterprise-data-engineering-frameworks.

Ensures that:
1. The project root is on ``sys.path`` so the top-level ``shared`` package
   is importable.
2. Hyphenated framework directories (e.g. ``etl-framework``) are registered
   as underscore Python packages (e.g. ``etl_framework``) so that imports
   like ``from etl_framework.pipeline import *`` resolve correctly.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# 1. Add root to sys.path so 'shared' is importable.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Directories that should not be treated as importable packages.
_NON_PACKAGE_DIRS = {
    "benchmarks", "docker", "docs", "examples", "kubernetes",
    "scripts", "templates", "tests", "__pycache__",
}

# 2. Register hyphenated directories as underscore package names.
for entry in sorted(ROOT.iterdir()):
    if not entry.is_dir() or entry.name.startswith("."):
        continue
    if entry.name in _NON_PACKAGE_DIRS:
        continue
    if (entry / "__init__.py").exists():
        pkg_name = entry.name.replace("-", "_")
        if pkg_name not in sys.modules:
            try:
                spec = importlib.util.spec_from_file_location(
                    pkg_name,
                    entry / "__init__.py",
                    submodule_search_locations=[str(entry)],
                )
                if spec is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[pkg_name] = module
                spec.loader.exec_module(module)
            except Exception:
                pass

# Keep pytest from trying to collect in non-package directories.
collect_ignore = [
    "benchmarks",
    "docker",
    "docs",
    "examples",
    "kubernetes",
    "scripts",
    "templates",
    "tests",
]
