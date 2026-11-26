# System Architecture: AWS Glue Serverless ETL & Cataloging Pipeline

This document describes the architectural framework, component interactions, and data lifecycle flow for the AWS Glue serverless ETL pipeline.

## System Component Diagram

The following Mermaid diagram visualizes the flow of data from ingestion to storage, detailing how crawlers, catalog metadata, Glue ETL jobs, validation rules, and monitoring systems interface.

```mermaid
graph TD
    %% Ingestion Sources
    subgraph Ingestion_S3 ["Ingestion Zone (S3)"]
        RawS3["Raw Bucket: s3://.../raw/sales/ <br>(Unstructured/CSV files)"]
    end

    %% AWS Glue Metadata & Catalog
    subgraph Catalog_Service ["AWS Glue Data Catalog"]
        Crawler["Glue Crawler <br>(ecommerce_sales_crawler)"]
        CatalogDB[("Glue Database: ecommerce_db")]
        RawTable["Raw Table Definition: raw_sales"]
        ProcessedTable["Processed Table Definition: processed_sales"]
    end

    %% AWS Glue Serverless Compute
    subgraph ETL_Compute ["AWS Glue Spark ETL Engine"]
        JobInit["Job Init (Job Bookmarks Activated)"]
        S3Read["S3 Connector Read <br>(DynamicFrame Object)"]
        DQDLCheck{"Glue Data Quality Engine <br>(DQDL Ruleset)"}
        
        subgraph Operations ["DynamicFrame Transformations"]
            ResolveChoice["resolveChoice <br>(Type Casting)"]
            DropNull["dropNullFields <br>(Prune Null Columns)"]
            Unnest["unnest <br>(Flatten Nested Structs)"]
            SelectFields["selectFields <br>(Prune Schema columns)"]
        end
        
        WriteSink["S3 Sink Writer <br>(Snappy Parquet Format)"]
    end

    %% Dest Zone
    subgraph Storage_Zone ["Curated Storage Zone (S3)"]
        CuratedS3["Processed Bucket: s3://.../processed/sales/ <br>(Partitioned: region=*)"]
    end

    %% Observability & Alerts
    subgraph Observability ["Observability & Alerts"]
        CWLogs["CloudWatch Logs <br>(Continuous Streaming)"]
        CWMetrics["CloudWatch Metrics <br>(RawRecords, ProcessedRecords, Success/Fail)"]
        SNSAlerts["Amazon SNS Topic <br>(Email / SMS Alerts)"]
    end

    %% Control Flow / Connections
    RawS3 --> Crawler
    Crawler -->|Catalog Scan & Schema Schema Inference| CatalogDB
    CatalogDB -->|Defines Schema for| RawTable
    
    RawS3 -->|Read Object Stream| S3Read
    JobInit --> S3Read
    S3Read --> DQDLCheck
    
    %% DQ Flow Paths
    DQDLCheck -->|PASS| ResolveChoice
    DQDLCheck -->|FAIL| SNSAlerts
    DQDLCheck -->|FAIL| Abort["Abort Job Execution"]

    ResolveChoice --> DropNull
    DropNull --> Unnest
    Unnest --> SelectFields
    SelectFields --> WriteSink
    
    WriteSink -->|Write Partitions| CuratedS3
    CuratedS3 -->|Registered Metadata Sync| ProcessedTable
    
    %% Monitoring Streams
    ETL_Compute -.->|Continuous Logging| CWLogs
    ETL_Compute -.->|Emit Metrics| CWMetrics
    Abort -.->|Publish Failure Event| SNSAlerts
```

## Step-by-Step Data Flow

1. **Ingestion Trigger / S3 Upload**:
   Raw transactional CSV records are loaded into the target S3 prefix (`s3://data-engineering-diaries-glue-demo/raw/sales/`).
2. **Metadata Discovery & Cataloging**:
   - The **Glue Crawler** (`ecommerce_sales_crawler`) runs scheduled (daily) or on-demand.
   - It crawls the raw directory, determines file structure, infers types, and registers/updates the database schema definitions inside the **Glue Data Catalog** database `ecommerce_db` under table name `raw_sales`.
3. **ETL Compute Bootstrapping**:
   - The **AWS Glue ETL Job** is triggered via a Workflow or On-Demand.
   - It boots up a Spark-managed serverless environment with selected workers (`G.1X` workers).
   - `Job Bookmarks` are loaded. The bookmark registers which files in the raw prefix have already been consumed by previous successful job runs to guarantee incremental ingestion.
4. **Data Validation (DQDL Engine)**:
   - The raw files are loaded into an AWS Glue `DynamicFrame` object.
   - The **AWS Glue Data Quality (DQDL)** ruleset runs. If validations pass, the pipeline continues. If validation fails, metrics are written to S3, a notification is sent to Amazon SNS, and the job aborts.
5. **Schema Alignment & Transform**:
   - `resolveChoice` converts column types (e.g. string fields like `revenue` and `discount` cast to `double`).
   - `dropNullFields` drops columns that contain no data.
   - `unnest` flattens nested columns.
   - `selectFields` ensures only required columns remain in the output schema.
6. **Partitioned Parquet Sink Write**:
   - The transformed data is written back to S3 under `s3://data-engineering-diaries-glue-demo/processed/sales/` in **Snappy Parquet** format.
   - It is partitioned by `region`, producing folders like `region=North/`, `region=South/` etc.
7. **Job State Update**:
   - The job commits the Job Bookmark state, marking the files as processed.
   - Custom metrics (record counts, execution duration) are published to CloudWatch metrics.
