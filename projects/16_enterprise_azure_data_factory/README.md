# 16 - Enterprise Azure Data Factory

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)]() [![Azure](https://img.shields.io/badge/azure-Data%20Factory-orange.svg)]() [![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

> **Project 16 in Production Data Engineering Projects**  
> Enterprise-grade Azure Data Factory cloud integration.

---

## 📚 Table of Contents

- [Overview](#-overview)
- [ADF Architecture](#-adf-architecture)
- [Folder Structure](#-folder-structure)
- [Modules](#-modules)

---

## 🎯 Overview

Azure Data Factory patterns for enterprise:

- Cloud data integration
- Metadata-driven ETL
- Pipeline orchestration
- CI/CD

---

## ⚙️ ADF Architecture

```mermaid
flowchart LR
    A[Source] --> B[ADF Pipeline]
    B --> C[ADF Data Flow]
    C --> D[Databricks]
    D --> E[Delta Lake]
```

---

## 📁 Folder Structure

```
16_enterprise_azure_data_factory/
├── README.md
├── adf/
│   ├── pipelines/
│   ├── datasets/
│   └── linked_services/
├── cicd/
└── tests/
```

---

*Enterprise Azure Data Factory.*