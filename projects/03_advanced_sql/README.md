# 03 - Advanced SQL for Data Engineering

[![Project Status](https://img.shields.io/badge/status-coming%20soon-orange)]()

> **Project 03 in Production Data Engineering Projects**

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

Advanced SQL patterns including window functions, CTEs, query optimization, and data warehousing techniques for enterprise-scale data engineering.

---

## 💼 Business Problem

Complex business analytics require advanced SQL patterns. Understanding window functions, hierarchical queries, and performance optimization is essential for building efficient data warehouses.

---

## 💡 Solution

Implementation of:
- Window functions (ROW_NUMBER, RANK, LAG, LEAD)
- Recursive CTEs for hierarchical data
- Advanced indexing strategies
- Query execution plan analysis

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Source Systems                           │
│              (Transactional DBs)                        │
├─────────────────────────────────────────────────────────┤
│                 Processing Layer                         │
│         (Analytics Queries, Aggregations)                │
├─────────────────────────────────────────────────────────┤
│                 Storage Layer                            │
│              (Data Warehouse)                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure

```
03_advanced_sql/
├── README.md
├── architecture.md
├── design-decisions.md
├── performance.md
├── troubleshooting.md
├── interview-questions.md
├── sample-data/
│   ├── raw/
│   └── processed/
├── src/
│   ├── __init__.py
│   └── queries/
├── tests/
├── images/
├── notebooks/
└── configs/
```

---

## 🛠️ Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| SQL | - | Query language |
| PostgreSQL | 15+ | Primary database |
| Explain | - | Query plan analysis |

---

## 📦 Prerequisites

- SQL fundamentals
- PostgreSQL installed

---

## 🔧 Installation

```bash
cd projects/03_advanced_sql
pip install -r requirements.txt
```

---

## ▶️ Running the Project

```bash
python -m src.main
```

---

## 🎯 Interview Questions

- Explain the difference between RANK() and DENSE_RANK()
- How do window functions differ from GROUP BY?
- What is a recursive CTE and when would you use it?