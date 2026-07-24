#!/bin/bash
# Create documentation placeholders for all projects

PROJECTS=(
    "01_python_fundamentals"
    "02_sql_for_data_engineering"
    "03_advanced_sql"
    "04_python_etl"
    "05_pyspark_basics"
    "06_delta_lake"
    "07_databricks"
    "08_airflow"
    "09_kafka"
    "10_streaming"
    "11_dbt"
    "12_snowflake"
    "13_azure_data_factory"
    "14_azure_databricks"
    "15_aws_glue"
    "16_emr"
    "17_redshift"
    "18_data_quality"
    "19_data_governance"
    "20_capstone"
)

for PROJECT in "${PROJECTS[@]}"; do
    PROJECT_DIR="projects/$PROJECT"
    
    # Create performance.md
    cat > "$PROJECT_DIR/performance.md" << 'EOF'
# Performance - PROJECT_NAME

## Benchmarks

Performance benchmarks will be documented with implementation.

## Optimization Strategies

Key optimization strategies for this technology stack.

## Resource Requirements

Minimum and recommended hardware/software requirements.
EOF

    # Create troubleshooting.md
    cat > "$PROJECT_DIR/troubleshooting.md" << 'EOF'
# Troubleshooting - PROJECT_NAME

## Common Issues

### Issue 1
**Symptom**: Description
**Solution**: Resolution steps

## Debug Commands

Useful commands for debugging and diagnostics.

## Logs Location

Where to find logs and monitoring information.
EOF

    # Create interview-questions.md
    cat > "$PROJECT_DIR/interview-questions.md" << 'EOF'
# Interview Questions - PROJECT_NAME

## Technical Questions

1. Question 1
2. Question 2
3. Question 3

## System Design Questions

- How would you scale this solution?
- What are the failure scenarios?
- How do you monitor performance?
EOF

    # Create requirements.txt
    cat > "$PROJECT_DIR/requirements.txt" << 'EOF'
# Requirements for PROJECT_NAME
# Will be populated during implementation

# Core dependencies
# Testing
pytest>=8.0.0
pytest-cov>=5.0.0
EOF

    # Create configs
    cat > "$PROJECT_DIR/configs/dev.yaml" << 'EOF'
# Development configuration
environment: development
debug: true
log_level: DEBUG
EOF

    cat > "$PROJECT_DIR/configs/staging.yaml" << 'EOF'
# Staging configuration
environment: staging
debug: false
log_level: INFO
EOF

    cat > "$PROJECT_DIR/configs/prod.yaml" << 'EOF'
# Production configuration
environment: production
debug: false
log_level: WARNING
EOF

    # Create tests/__init__.py
    touch "$PROJECT_DIR/tests/__init__.py"

    # Create tests/conftest.py
    cat > "$PROJECT_DIR/tests/conftest.py" << 'EOF'
"""Pytest configuration and shared fixtures."""
import pytest


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {"environment": "test", "batch_size": 100}
EOF

    # Create src/__init__.py
    cat > "$PROJECT_DIR/src/__init__.py" << 'EOF'
"""Project source modules."""
__version__ = "0.1.0"
EOF

    # Create tests/unit/__init__.py
    touch "$PROJECT_DIR/tests/unit/__init__.py"

    # Create tests/integration/__init__.py
    touch "$PROJECT_DIR/tests/integration/__init__.py"

    echo "Created documentation for $PROJECT"
done

echo "All project documentation created!"