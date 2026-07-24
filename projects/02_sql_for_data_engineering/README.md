# 02 - SQL for Data Engineering

[![Project Status](https://img.shields.io/badge/status-coming%20soon-orange)]()

> **Project 02 in Production Data Engineering Projects**

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Business Problem](#-business-problem)
- [Solution](#-solution)
- [Architecture](#-architecture)
- [Folder Structure](#-folder-structure)
- [Technology Stack](#-technology-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the Project](#-running-the-project)
- [Output](#-output)
- [Performance](#-performance)
- [Future Improvements](#-future-improvements)
- [Key Learnings](#-key-learnings)
- [Interview Questions](#-interview-questions)
- [References](#-references)

---

## 🎯 Overview

Essential SQL techniques for data engineering workflows. This project covers fundamental SQL operations used in data engineering, including joins, aggregations, subqueries, and common data transformation patterns.

---

## 💼 Business Problem

Data engineers need to extract, transform, and analyze data efficiently using SQL. Writing performant queries and understanding query execution plans is crucial for building scalable data pipelines.

---

## 💡 Solution

Learn and implement:
- SELECT, JOIN, and GROUP BY optimization
- Subqueries and Common Table Expressions (CTEs)
- Data modeling fundamentals
- Query performance tuning

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Source Systems                           │
│              (Databases, APIs, Files)                    │
├─────────────────────────────────────────────────────────┤
│                 Processing Layer                         │
│         (SQL Queries, Views, Stored Procedures)          │
├─────────────────────────────────────────────────────────┤
│                 Storage Layer                            │
│               (Data Warehouse)                           │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure

```
02_sql_for_data_engineering/
├── README.md                    # This file
├── architecture.md             # System architecture details
├── design-decisions.md         # Architectural decisions
├── performance.md              # Performance benchmarks
├── troubleshooting.md            # Common issues and solutions
├── interview-questions.md        # Interview preparation
├── sample-data/                # Sample datasets
│   ├── raw/                   # Raw input data
│   └── processed/             # Processed output data
├── src/                        # Source code
│   ├── __init__.py
│   ├── queries/
│   └── scripts/
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── images/                     # Architecture diagrams
├── notebooks/                  # Jupyter notebooks
└── configs/                    # Configuration files
    ├── dev.yaml
    ├── staging.yaml
    └── prod.yaml
```

---

## 🛠️ Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| SQL | - | Query language |
| PostgreSQL | 15+ | Primary database |
| SQLite | 3.x | Local testing |

---

## 📦 Prerequisites

- SQL basics
- PostgreSQL or SQLite installed

---

## 🔧 Installation

```bash
# Navigate to project directory
cd projects/02_sql_for_data_engineering

# Install dependencies
pip install -r requirements.txt
```

---

## ▶️ Running the Project

```bash
# Run SQL scripts
python -m src.main

# Run tests
pytest tests/ -v
```

---

## 📊 Output

Query results with proper optimization and validation.

---

## ⚡ Performance

Performance benchmarks will be documented with implementation.

---

## 🚀 Future Improvements

- [ ] Add window function examples
- [ ] Include query plan analysis
- [ ] Add materialized view patterns

---

## 📚 Key Learnings

- Proper indexing strategies
- Query optimization techniques
- Data modeling principles
- SQL performance tuning

---

## 🎯 Interview Questions

1. **Explain different JOIN types**: INNER, LEFT, RIGHT, FULL OUTER with examples.

2. **What is a CTE and when to use it?**: Common Table Expressions improve readability.

3. **How do you optimize a slow query?**: Index analysis, query rewrite, execution plans.

---

## 📖 References

- [PostgreSQL Documentation](https://postgresql.org/docs/)
- [SQL Performance Explained](https://sql-performance-explained.com/)
- [Modern SQL](https://modern-sql.com/)