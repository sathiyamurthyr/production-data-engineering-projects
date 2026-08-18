"""Tests for the Global Banking architecture validation."""

import os
from pathlib import Path


ARCH_DIR = Path(__file__).resolve().parent.parent


def test_architecture_docs_exist():
    """Verify all required architecture documents exist."""
    required_docs = [
        "executive-summary.md",
        "business-case.md",
        "problem-statement.md",
        "requirements.md",
        "architecture-overview.md",
        "architecture-principles.md",
        "architecture-decisions.md",
        "business-architecture.md",
        "application-architecture.md",
        "data-architecture.md",
        "technology-architecture.md",
        "integration-architecture.md",
        "security-architecture.md",
        "deployment-architecture.md",
        "network-concepts.md",
        "identity-strategy.md",
        "monitoring-strategy.md",
        "operations-guide.md",
        "disaster-recovery.md",
        "capacity-planning.md",
        "cost-analysis.md",
        "risk-analysis.md",
        "migration-strategy.md",
        "implementation-roadmap.md",
        "best-practices.md",
        "anti-patterns.md",
        "troubleshooting.md",
        "interview-questions.md",
        "references.md",
    ]
    for doc in required_docs:
        assert (ARCH_DIR / doc).exists(), f"Missing: {doc}"


def test_readme_exists():
    """Verify README exists."""
    assert (ARCH_DIR / "README.md").exists()


def test_architecture_diagrams_exist():
    """Verify architecture diagrams exist."""
    diagrams_dir = ARCH_DIR / "diagrams"
    assert diagrams_dir.exists(), "Missing diagrams directory"
    diagram_count = len(list(diagrams_dir.glob("*.mmd")))
    assert diagram_count >= 5, f"Only {diagram_count} diagrams found"


def test_implementations_exist():
    """Verify implementation directories exist."""
    impl_dir = ARCH_DIR / "implementations"
    assert impl_dir.exists(), "Missing implementations directory"
    required_dirs = ["terraform", "cicd", "pipelines", "api", "data-models"]
    for d in required_dirs:
        assert (impl_dir / d).exists(), f"Missing implementations/{d}"


def test_adr_exists():
    """Verify at least one ADR exists."""
    adr_dir = ARCH_DIR / "architecture-decision-records"
    assert adr_dir.exists(), "Missing ADR directory"
    adr_count = len(list(adr_dir.glob("*.md")))
    assert adr_count >= 1, f"Only {adr_count} ADRs found"
