# Contributing Guide

First off, thank you for considering contributing to **Production Data Engineering Projects**! It's people like you that make this repository great.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Documentation Standards](#documentation-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Commit Message Guidelines](#commit-message-guidelines)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### 🐛 Report Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Provide specific examples to demonstrate the bug
- Explain what you expected to happen and what actually happened
- Include your Python version, OS, and any relevant version information

### ✨ Feature Requests

Feature requests are welcome! But take a moment to find out whether your idea fits with the scope and aim of the project. When ready:

- Use a clear and descriptive title
- Provide a step-by-step description of the suggested feature
- Explain why this feature would be useful
- List any similar features in other data engineering projects

### 📝 Pull Requests

- Fill in the required template
- Do not include issue numbers in the PR title
- Follow the coding standards
- Include tests for new functionality
- Update documentation for any new features
- End all files with a newline

## Development Setup

### Prerequisites

- Python 3.13 or higher
- Docker and Docker Compose
- Git
- Make (optional, for using make commands)

### Setup Steps

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/production-data-engineering-projects.git
cd production-data-engineering-projects

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Verify setup
pre-commit run --all-files
```

### Development Dependencies

`requirements-dev.txt`:
```txt
# Testing
pytest>=8.0.0
pytest-cov>=5.0.0
pytest-mock>=3.12.0

# Code Quality
black>=24.0.0
ruff>=0.6.0
mypy>=1.11.0
types-all>=0.0.0

# Documentation
mkdocs>=1.5.0
mkdocs-material>=9.0.0

# Pre-commit
pre-commit>=3.0.0
detect-secrets>=1.0.0

# Development Tools
commitizen>=3.29.0
```

## Project Structure

Each project follows a consistent structure:

```
project_name/
├── README.md                    # Project overview and documentation
├── architecture.md             # System architecture
├── design-decisions.md         # Architecture decisions and trade-offs
├── performance.md              # Performance benchmarks and optimizations
├── troubleshooting.md            # Common issues and solutions
├── interview-questions.md        # Interview preparation guide
├── sample-data/                # Sample datasets
│   ├── raw/
│   └── processed/
├── src/                        # Source code
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   └── main.py
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── images/                     # Architecture diagrams and visuals
├── notebooks/                  # Jupyter notebooks (if applicable)
└── configs/                    # Configuration files
    ├── dev.yaml
    ├── staging.yaml
    └── prod.yaml
```

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions
- Use type hints for all functions and classes
- Use docstrings for all public modules, functions, classes, and methods
- Use logging instead of print statements
- No hardcoded values - use environment variables or config files
- Handle errors gracefully with proper exception handling

### Example Code Style

```python
"""Module for data validation utilities."""

from typing import Any

import pandas as pd
from pydantic import BaseModel, ValidationError


class DataRecord(BaseModel):
    """Schema definition for data records."""

    id: int
    name: str
    value: float

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate DataFrame against schema.

    Args:
        df: Input DataFrame to validate.

    Returns:
        Validated DataFrame with proper types.

    Raises:
        ValidationError: If data doesn't match schema.
    """
    records = df.to_dict(orient="records")
    validated = [DataRecord(**record) for record in records]
    return pd.DataFrame([r.model_dump() for r in validated])
```

## Documentation Standards

### README Format

Every project README must include:

1. **Project Overview** - Brief description of the project
2. **Business Problem** - Real-world use case
3. **Solution** - How the project solves the problem
4. **Architecture** - System diagram and explanation
5. **Folder Structure** - Project organization
6. **Technology Stack** - Tools and versions used
7. **Prerequisites** - Required software and accounts
8. **Installation** - Setup instructions
9. **Running the Project** - How to execute
10. **Output** - Expected results
11. **Performance** - Benchmarks and metrics
12. **Future Improvements** - Next steps
13. **Key Learnings** - Important takeaways
14. **Interview Questions** - Common interview topics
15. **References** - Further reading

### Documentation Templates

Use templates from `/templates/` folder for consistency.

## Testing Requirements

### Test Structure

```
tests/
├── unit/                       # Unit tests for individual components
├── integration/                # Integration tests for workflows
├── fixtures/                   # Test data and fixtures
└── conftest.py                 # Pytest configuration and shared fixtures
```

### Testing Guidelines

- Minimum 80% code coverage
- Use pytest for all test frameworks
- Write descriptive test names
- Include both positive and negative test cases
- Mock external dependencies (databases, APIs)
- Use fixtures for test setup

### Example Test

```python
def test_validate_dataframe_valid_input(sample_dataframe: pd.DataFrame) -> None:
    """Test that validate_dataframe processes valid data correctly."""
    result = validate_dataframe(sample_dataframe)

    assert len(result) == len(sample_dataframe)
    assert "id" in result.columns
    assert result["id"].dtype == "int64"
```

## Pull Request Process

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/project-name-description
   ```

2. **Make Changes**
   - Follow coding standards
   - Write/update tests
   - Update documentation

3. **Run Quality Checks**
   ```bash
   pre-commit run --all-files
   pytest tests/ --cov=projects
   ```

4. **Push Changes**
   ```bash
   git push origin feature/project-name-description
   ```

5. **Create Pull Request**
   - Fill out the PR template
   - Link related issues
   - Wait for review and CI checks

### PR Requirements

- [ ] All tests pass
- [ ] Code coverage maintained or improved
- [ ] No linting errors
- [ ] Type checking passes
- [ ] Documentation updated
- [ ] Changes reviewed by maintainer

## Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only changes
- `style` - Code style changes (formatting, etc.)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

### Examples

```
feat(pyspark): add partition pruning optimization

Add implementation for partition pruning in Spark pipelines
to improve query performance by 40%.

Closes #123
```

```
docs: update airflow deployment documentation

Add section on Kubernetes executor configurations
and troubleshooting tips.
```

## Questions?

Feel free to open an issue with the `question` label, and we'll help you out!

---

Thank you for contributing to making this repository world-class! 🎉