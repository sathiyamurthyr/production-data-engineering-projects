# 05 - PySpark Basics

[![Project Status](https://img.shields.io/badge/status-coming%20soon-orange)]()

> **Project 05 in Production Data Engineering Projects**

---

## 🎯 Overview

Introduction to PySpark for big data processing. This project covers Spark fundamentals, DataFrame API, transformations, and actions.

---

## 💼 Business Problem

Processing large datasets that don't fit in memory requires distributed computing. PySpark provides the foundation for big data engineering at scale.

---

## 💡 Solution

Learn and implement:
- SparkSession and SparkContext
- DataFrame transformations (map, filter, join)
- Action operations (collect, count, write)
- File format handling (CSV, Parquet, JSON)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Driver Program                           │
│              (Application Code)                            │
├─────────────────────────────────────────────────────────┤
│                 Cluster                                    │
│         (Executors, Tasks, Partitions)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.13+ | Programming language |
| PySpark | 3.5+ | Big data processing |
| Spark | 3.5+ | Distributed compute |

---

## 🎯 Interview Questions

- What is the difference between RDD and DataFrame?
- Explain Spark's lazy evaluation
- How does partitioning work in Spark?
- What are broadcast variables?