#!/usr/bin/env bash
#
# create_pattern.sh - Scaffold a new design pattern with all required files.
#
# Usage: ./scripts/create_pattern.sh <category> <pattern-name> <display-name>
#
# Example:
#   ./scripts/create_pattern.sh architecture-patterns medallion-architecture "Medallion Architecture"
#
set -euo pipefail

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <category> <pattern-name> <display-name>"
    echo "Example: $0 architecture-patterns medallion-architecture 'Medallion Architecture'"
    exit 1
fi

CATEGORY="$1"
PATTERN_NAME="$2"
DISPLAY_NAME="$3"
PATTERN_DIR="${CATEGORY}/${PATTERN_NAME}"

# Sanitize name for file naming
SAFE_NAME=$(echo "$PATTERN_NAME" | tr '-' '_')
CLASS_NAME=$(echo "$PATTERN_NAME" | sed 's/-/ /g' | sed 's/.*/\u&/' | sed 's/ //g')

echo "Creating pattern '${DISPLAY_NAME}' in ${PATTERN_DIR}..."

# Create directory structure
mkdir -p "${PATTERN_DIR}/src"
mkdir -p "${PATTERN_DIR}/tests"
mkdir -p "${PATTERN_DIR}/benchmarks"
mkdir -p "${PATTERN_DIR}/datasets"
mkdir -p "${PATTERN_DIR}/mermaid"
mkdir -p "${PATTERN_DIR}/infrastructure"

# Create __init__.py files
cat > "${PATTERN_DIR}/src/__init__.py" <<EOF
"""${DISPLAY_NAME} pattern implementation.

Business Problem:
    [Fill in the specific business problem this pattern addresses]

Context:
    [Fill in the context and when to use this pattern]

Tags:
    - ${CATEGORY}
    - ${DISPLAY_NAME}
"""
EOF

# Create main implementation file
cat > "${PATTERN_DIR}/src/${SAFE_NAME}.py" <<EOF
"""${DISPLAY_NAME} pattern - Production implementation.

This module implements the ${DISPLAY_NAME} pattern with:
- [List key implementation features]
- [List key implementation features]

Typical use cases:
    [List typical use cases]

References:
    [List references]
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ${CLASS_NAME}Config(BaseModel):
    """Configuration for the ${DISPLAY_NAME} pattern."""

    pattern_name: str = Field(default="${PATTERN_NAME}")
    # Add configuration fields specific to this pattern


class ${CLASS_NAME}:
    """${DISPLAY_NAME} pattern implementation.

    Args:
        config: Pattern configuration.

    Example:
        >>> config = ${CLASS_NAME}Config()
        >>> pattern = ${CLASS_NAME}(config)
        >>> pattern.execute()
    """

    def __init__(self, config: ${CLASS_NAME}Config | None = None) -> None:
        self.config = config or ${CLASS_NAME}Config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def execute(self, data: Any) -> Any:
        """Execute the ${DISPLAY_NAME} pattern.

        Args:
            data: Input data to process.

        Returns:
            Processed data according to the pattern.
        """
        self.logger.info("Executing ${DISPLAY_NAME} pattern", pattern=self.config.pattern_name)
        # Implementation goes here
        return data
EOF

# Create test file
cat > "${PATTERN_DIR}/tests/__init__.py" <<EOF
EOF

cat > "${PATTERN_DIR}/tests/test_${SAFE_NAME}.py" <<EOF
"""Unit tests for the ${DISPLAY_NAME} pattern."""

import pytest

from src.${SAFE_NAME} import ${CLASS_NAME}, ${CLASS_NAME}Config


class Test${CLASS_NAME}Config:
    """Tests for ${CLASS_NAME}Config."""

    def test_default_config(self) -> None:
        config = ${CLASS_NAME}Config()
        assert config.pattern_name == "${PATTERN_NAME}"


class Test${CLASS_NAME}:
    """Tests for ${CLASS_NAME}."""

    def test_init_default_config(self) -> None:
        pattern = ${CLASS_NAME}()
        assert pattern.config.pattern_name == "${PATTERN_NAME}"

    def test_init_custom_config(self) -> None:
        config = ${CLASS_NAME}Config()
        pattern = ${CLASS_NAME}(config)
        assert pattern.config == config
EOF

# Create benchmark file
cat > "${PATTERN_DIR}/benchmarks/benchmark_${SAFE_NAME}.py" <<EOF
"""Benchmarks for the ${DISPLAY_NAME} pattern."""

from __future__ import annotations

import time

from src.${SAFE_NAME} import ${CLASS_NAME}, ${CLASS_NAME}Config


def benchmark_execute() -> None:
    """Benchmark the execute method."""
    pattern = ${CLASS_NAME}()
    data = "sample_data"

    start = time.perf_counter()
    for _ in range(1000):
        pattern.execute(data)
    elapsed = time.perf_counter() - start

    print(f"1000 executions: {elapsed:.4f}s ({elapsed/1000*1000:.2f}ms per call)")


if __name__ == "__main__":
    benchmark_execute()
EOF

# Create mermaid diagram
cat > "${PATTERN_DIR}/mermaid/architecture.mmd" <<EOF
%%${DISPLAY_NAME} Architecture Diagram
graph LR
    A[Input] --> B[Processing]
    B --> C[Output]
EOF

# Create README.md
cat > "${PATTERN_DIR}/README.md" <<EOF
# ${DISPLAY_NAME} Pattern

## Business Problem

[Describe the specific business problem this pattern addresses]

## Context

[Describe the context, when to use this pattern, and the forces at play]

## Architecture

\`\`\`mermaid
$(cat "${PATTERN_DIR}/mermaid/architecture.mmd")
\`\`\`

### Components

[List and describe the key components]

## Decision Criteria

[When to use this pattern vs alternatives]

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Factor] | [Choice] | [Why this choice] |

## Advantages

- [Advantage 1]
- [Advantage 2]

## Limitations

- [Limitation 1]
- [Limitation 2]

## Performance Considerations

[Performance implications and optimization tips]

## Security Considerations

[Security implications and best practices]

## Cost Considerations

[Cost implications and optimization strategies]

## Operational Guidance

[Operational best practices, monitoring, alerting]

## Anti-patterns

[List common misuse scenarios and how to avoid them]

## Real Enterprise Use Cases

[List real enterprise use cases]

## References

[List references and further reading]
EOF

# Create remaining documentation files
cat > "${PATTERN_DIR}/architecture.md" <<EOF
# ${DISPLAY_NAME} - Architecture

## Overview

[High-level architecture description]

## Diagram

\`\`\`mermaid
$(cat "${PATTERN_DIR}/mermaid/architecture.mmd")
\`\`\`

## Component Details

### [Component Name]

[Description]

## Data Flow

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Layer Interactions

[Layer interaction description]
EOF

cat > "${PATTERN_DIR}/implementation.md" <<EOF
# ${DISPLAY_NAME} - Implementation

## Quick Start

\`\`\`bash
# Install dependencies
pip install -r ${PATTERN_DIR}/requirements.txt

# Run the pattern
python -m src.${SAFE_NAME}
\`\`\`

## Configuration

\`\`\`python
from src.${SAFE_NAME} import ${CLASS_NAME}Config, ${CLASS_NAME}

config = ${CLASS_NAME}Config(
    pattern_name="${PATTERN_NAME}",
)
pattern = ${CLASS_NAME}(config)
\`\`\`

## Production Deployment

\`\`\`bash
# Deploy with Docker
docker build -t ${PATTERN_NAME}:latest -f ${PATTERN_DIR}/infrastructure/Dockerfile .
docker run -d --name ${PATTERN_NAME} ${PATTERN_NAME}:latest
\`\`\`

## Error Handling

[Error handling strategy]

## Monitoring

[Monitoring and observability strategy]
EOF

cat > "${PATTERN_DIR}/decision-matrix.md" <<EOF
# ${DISPLAY_NAME} - Decision Matrix

## When to Use ${DISPLAY_NAME}

| Scenario | Use Pattern | Don't Use | Rationale |
|----------|-------------|-----------|-----------|
| [Scenario 1] | ✅ | ❌ | [Rationale] |
| [Scenario 2] | ✅ | ❌ | [Rationale] |

## Comparison with Alternative Patterns

| Pattern | Pros | Cons | Best For |
|---------|------|------|----------|
| ${DISPLAY_NAME} | [Pros] | [Cons] | [Best For] |
| [Alternative] | [Pros] | [Cons] | [Best For] |

## Selection Criteria

1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]
EOF

cat > "${PATTERN_DIR}/anti-patterns.md" <<EOF
# ${DISPLAY_NAME} - Anti-patterns

## Common Mistakes

### [Anti-pattern Name 1]

**What happens:**

[Description of the anti-pattern]

**Consequences:**

- [Consequence 1]
- [Consequence 2]

**How to avoid:**

[Guidance on how to avoid this anti-pattern]

### [Anti-pattern Name 2]

**What happens:**

[Description]

**Consequences:**

- [Consequence 1]
- [Consequence 2]

**How to avoid:**

[Guidance]
EOF

cat > "${PATTERN_DIR}/performance.md" <<EOF
# ${DISPLAY_NAME} - Performance

## Benchmarks

| Metric | Value | Notes |
|--------|-------|-------|
| Throughput | [value] | [notes] |
| Latency (p50) | [value] | [notes] |
| Latency (p99) | [value] | [notes] |
| Memory usage | [value] | [notes] |

## Optimization Strategies

[Optimization strategies]

## Resource Utilization

[Resource utilization analysis]
EOF

cat > "${PATTERN_DIR}/security.md" <<EOF
# ${DISPLAY_NAME} - Security

## Threat Model

[Threat model description]

## Security Controls

| Control | Implementation | Status |
|---------|----------------|--------|
| [Control] | [Implementation] | ✅/❌ |

## Compliance Considerations

[Compliance considerations]

## Secrets Management

[Secrets management strategy]
EOF

cat > "${PATTERN_DIR}/operations.md" <<EOF
# ${DISPLAY_NAME} - Operations

## Monitoring

[Monitoring strategy and metrics]

## Alerting

[Alerting thresholds and conditions]

## Runbooks

[Operational runbooks]

## Capacity Planning

[Capacity planning guidance]
EOF

cat > "${PATTERN_DIR}/cost-analysis.md" <<EOF
# ${DISPLAY_NAME} - Cost Analysis

## Cost Drivers

[List of cost drivers]

## Cost Comparison

| Option | Monthly Cost | Notes |
|--------|-------------|-------|
| [Option 1] | [cost] | [notes] |
| [Option 2] | [cost] | [notes] |

## Optimization Strategies

[Cost optimization strategies]
EOF

cat > "${PATTERN_DIR}/deployment-guide.md" <<EOF
# ${DISPLAY_NAME} - Deployment Guide

## Prerequisites

[List prerequisites]

## Infrastructure

[Infrastructure as Code]

## Deployment Steps

1. [Step 1]
2. [Step 2]

## Verification

[Verification steps]
EOF

cat > "${PATTERN_DIR}/troubleshooting.md" <<EOF
# ${DISPLAY_NAME} - Troubleshooting

## Common Issues

### [Issue 1]

**Symptom:**

[Description of the symptom]

**Root Cause:**

[Root cause analysis]

**Resolution:**

[Resolution steps]

### [Issue 2]

**Symptom:**

[Description]

**Root Cause:**

[Root cause]

**Resolution:**

[Resolution steps]
EOF

cat > "${PATTERN_DIR}/interview-questions.md" <<EOF
# ${DISPLAY_NAME} - Interview Questions

## Beginner

1. **What is the ${DISPLAY_NAME} pattern?**
   [Answer]

2. **When would you use this pattern?**
   [Answer]

## Intermediate

1. **What are the key trade-offs?**
   [Answer]

2. **How do you handle [specific scenario]?**
   [Answer]

## Advanced

1. **How would you scale this pattern?**
   [Answer]

2. **What are the production considerations?**
   [Answer]
EOF

cat > "${PATTERN_DIR}/requirements.txt" <<EOF
# ${DISPLAY_NAME} dependencies
EOF

echo "Pattern '${DISPLAY_NAME}' created at ${PATTERN_DIR}"
echo "Files created:"
find "${PATTERN_DIR}" -type f | sort | while read -r f; do
    echo "  - ${f}"
done
