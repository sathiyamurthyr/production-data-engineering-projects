# 18 - Enterprise AWS Glue, EMR & Lake Formation

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)]() [![AWS](https://img.shields.io/badge/aws-Glue%2FEMR-orange.svg)]() [![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

> **Project 18 in Production Data Engineering Projects**  
> Enterprise-grade AWS Data Engineering platform.

---

## 📚 Table of Contents

- [Overview](#-overview)
- [AWS Lakehouse Architecture](#-aws-lakehouse-architecture)
- [Folder Structure](#-folder-structure)
- [Modules](#-modules)

---

## 🎯 Overview

AWS Data Engineering patterns for enterprise:

- Glue crawlers and jobs
- EMR Spark processing
- Lake Formation governance
- Athena querying

---

## ⚙️ AWS Lakehouse Architecture

```mermaid
flowchart LR
    A[S3 Data Lake] --> B[Glue Crawler]
    B --> C[Glue Data Catalog]
    C --> D[Glue Job]
    D --> E[EMR Spark]
    E --> F[Bronze/Silver/Gold]
    F --> G[Athena]
```

---

## 📁 Folder Structure

```
18_enterprise_aws_glue_emr_lakeformation/
├── README.md
├── glue/
│   ├── jobs/
│   └── crawlers/
├── emr/
├── lakeformation/
└── terraform/
```

---

*Enterprise AWS Data Engineering.*