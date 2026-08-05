"""Pytest configuration for shared utility tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Add shared module to path for tests
shared_dir = Path(__file__).resolve().parent.parent / "shared"
sys.path.insert(0, str(shared_dir.parent))
