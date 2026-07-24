# 01 - Python Fundamentals for Data Engineering

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)]()
[![Tests](https://img.shields.io/badge/tests-25+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

> **Project 01 in Production Data Engineering Projects**  
> Complete Python fundamentals course designed specifically for data engineering workflows.

---

## 📚 Table of Contents

- [Overview](#-overview)
- [Learning Objectives](#-learning-objectives)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Project Structure](#-project-structure)
- [Topics Covered](#-topics-covered)
- [Running Examples](#-running-examples)
- [Exercises](#-exercises)
- [Solutions](#-solutions)
- [Architecture](#-architecture)
- [Best Practices](#-best-practices)
- [Interview Questions](#-interview-questions)
- [References](#-references)

---

## 🎯 Overview

This project teaches Python from a **data engineering perspective**, covering essential concepts through real-world examples:

- Building ETL pipelines
- Data validation and cleaning
- Configuration management
- Error handling and logging
- Working with APIs and databases
- Production-ready code patterns

---

## 🎓 Learning Objectives

By completing this project, you will be able to:

1. Write production-quality Python code with proper typing and error handling
2. Build ETL pipelines using built-in Python libraries
3. Validate and transform data using Pydantic and Pandas
4. Handle configuration securely with environment variables
5. Implement structured logging for observability
6. Work with external APIs and databases
7. Debug and test Python code effectively

---

## 📦 Prerequisites

- Basic programming knowledge
- Python 3.13+ installed
- Understanding of data concepts (CSV, JSON, databases)

---

## 🔧 Installation

```bash
# Navigate to project directory
cd projects/01_python_fundamentals

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

---

## 📁 Project Structure

```
01_python_fundamentals/
├── README.md              # This file
├── architecture.md        # System architecture
├── design-decisions.md    # Architectural decisions
├── performance.md         # Performance benchmarks
├── troubleshooting.md      # Common issues
├── interview-questions.md  # Interview prep
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
├── configs/
│   ├── dev.yaml           # Development config
│   ├── staging.yaml       # Staging config
│   └── prod.yaml          # Production config
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── logger.py          # Structured logging
│   ├── models.py          # Pydantic models
│   ├── main.py            # Main ETL entry point
│   └── examples.py        # All concept examples
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Test fixtures
│   ├── test_examples.py   # Comprehensive tests
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── exercises/
│   ├── 01_variables.md
│   ├── 02_data_types.md
│   ├── 03_operators.md
│   ├── 04_strings.md
│   ├── 05_lists.md
│   └── ...                # More exercises
├── solutions/
│   ├── 01_variables.md
│   ├── 02_data_types.md
│   ├── 03_operators.md
│   └── ...                # Solutions for all exercises
├── notebooks/
│   └── 01_python_basics.ipynb  # Interactive examples
├── images/
│   └── etl_flow.md        # Architecture diagrams
└── sample-data/
    ├── raw/
    │   └── customers.csv
    └── processed/
```

---

## 📖 Topics Covered

| # | Topic | Business Use Case |
|---|-------|-------------------|
| 01 | Variables | Configuration storage |
| 02 | Data Types | Type-safe data processing |
| 03 | Operators | Filtering and aggregation |
| 04 | Strings | Column name cleaning, email parsing |
| 05 | Lists | Batch processing, record collections |
| 06 | Tuples | Immutable configuration |
| 07 | Sets | Deduplication, validation |
| 08 | Dictionaries | Record storage, config management |
| 09 | Loops | File processing, iterations |
| 10 | Functions | Modular transformations |
| 11 | Lambda | Inline data processing |
| 12 | List Comprehension | Efficient filtering |
| 13 | Exception Handling | Graceful error recovery |
| 14 | File Handling | CSV/JSON I/O |
| 15 | JSON | API responses, config files |
| 16 | CSV | Data ingestion |
| 17 | DateTime | Timestamps, incremental loads |
| 18 | Logging | Pipeline observability |
| 19 | Config Files | Environment configuration |
| 20 | Environment Variables | Secure secrets |
| 21 | Virtual Environment | Dependency isolation |
| 22 | Modules | Code organization |
| 23 | Packages | Project structure |
| 24 | OOP | ETL framework |
| 25 | Dataclasses | Clean data models |
| 26 | Typing | Type safety |
| 27 | Decorators | Cross-cutting concerns |
| 28 | Generators | Memory efficiency |
| 29 | Iterators | Custom iteration |
| 30 | Context Managers | Resource management |
| 31 | Regular Expressions | Data validation |
| 32 | API Requests | External data sources |
| 33 | REST API | Building services |
| 34 | SQLite | Local data storage |
| 35 | Pandas | Data analysis |
| 36 | Data Cleaning | Quality improvement |
| 37 | CLI Arguments | Configurable pipelines |
| 38 | OS Module | System operations |
| 39 | Pathlib | File path handling |
| 40 | Subprocess | External commands |
| 41 | Unit Testing | Testable code |
| 42 | Mock Testing | Isolated tests |
| 43 | Logging Best Practices | Production logging |
| 44 | Configuration Management | Flexible config |
| 45 | Mini ETL Project | Complete pipeline |

---

## ▶️ Running Examples

```python
# Run the main ETL pipeline
python -m src.main

# See all examples in action
python -c "from src.examples import *; demonstrate_data_types()"
```

---

## 💪 Exercises

Each exercise comes with solutions in the `solutions/` directory:

- **Easy**: Basic syntax and concepts
- **Medium**: Real-world scenarios
- **Hard**: Production-level challenges

---

## 🏗️ Architecture

```mermaid
graph LR
    A[Extract CSV] --> B[Transform with Examples]
    B --> C[Validate with Pydantic]
    C --> D[Load JSON]
    D --> E[Log Results]
```

---

## ✅ Best Practices

- Use type hints for all functions
- Validate all data inputs with Pydantic
- Use structured logging (structlog)
- Handle errors gracefully
- Use context managers for resources
- Write comprehensive tests
- Document with docstrings

---

## 🎯 Interview Questions

1. **Why use type hints in production code?**
2. **How do you handle configuration in different environments?**
3. **What's the difference between lists and tuples?**
4. **Explain context managers and their use in data engineering.**
5. **How do you implement retry logic in Python?**

See `interview-questions.md` for more.

---

## 📖 References

- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Logging Cookbook](https://docs.python.org/3/howto/logging.html)

---

*Production-ready Python fundamentals for data engineering professionals.*