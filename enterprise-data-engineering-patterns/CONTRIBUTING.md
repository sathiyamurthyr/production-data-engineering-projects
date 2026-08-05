# Contributing to Enterprise Data Engineering Patterns

Thank you for your interest in contributing! This repository aims to be the definitive reference for production-grade data engineering design patterns.

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to abide by its terms.

## How to Contribute

### 1. Fork and Clone

```bash
git fork https://github.com/sathiyamurthyr/enterprise-data-engineering-patterns.git
git clone https://github.com/<your-username>/enterprise-data-engineering-patterns.git
cd enterprise-data-engineering-patterns
```

### 2. Create a Branch

```bash
git checkout -b feature/add-<pattern-name>-pattern
```

### 3. Add a Pattern

Each pattern must include ALL of the following files:

```
<pattern-name>/
├── README.md                    # Business problem, context, summary
├── architecture.md              # Architecture diagram, components, relationships
├── implementation.md            # Production implementation guide
├── mermaid/                     # Mermaid diagrams
│   ├── architecture.mmd
│   └── flow.mmd
├── src/                         # Production code
│   ├── __init__.py
│   └── <pattern_name>.py
├── tests/                       # Unit tests (100% coverage required)
│   ├── __init__.py
│   └── test_<pattern_name>.py
├── benchmarks/                  # Performance benchmarks
│   └── benchmark_<pattern_name>.py
├── datasets/                    # Sample datasets
│   └── sample.json
├── deployment-guide.md          # Deployment instructions
├── troubleshooting.md           # Troubleshooting guide
├── interview-questions.md       # Interview questions
├── ADR-*.md                     # Architecture Decision Records
└── requirements.txt             # Language-specific dependencies
```

### 4. Follow Quality Standards

- **No placeholder code** — All implementations must be production-ready
- **No TODOs** — Code must be complete
- **Type hints** — All Python code must use type hints (Python 3.13+)
- **Unit tests** — 100% code coverage required
- **Documentation** — Every public class and function must have docstrings
- **PEP 8** — Follow Python style guide
- **Structured logging** — Use structlog for all logging
- **Security** — Consider security implications in every pattern

### 5. Run Quality Checks

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linter
ruff check .

# Run type checker
mypy .

# Run tests with coverage
pytest --cov=./ --cov-report=html

# Run formatter
black .
```

### 6. Commit and Push

```bash
git add .
git commit -m "feat: add <pattern-name> pattern"
git push origin feature/add-<pattern-name>-pattern
```

### 7. Create a Pull Request

Open a PR against the `main` branch. Ensure CI passes.

## Pattern Template

Use the [pattern template](templates/pattern-template/) as a starting point.

## Reporting Issues

Use the GitHub issue tracker to report bugs or request new patterns.

## Code Review Process

- All PRs require at least one reviewer
- CI must pass (tests, lint, type check)
- Code coverage must be 100%
- No TODOs or placeholder code allowed