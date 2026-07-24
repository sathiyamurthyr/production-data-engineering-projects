# Data Warehouse Architecture

## Star Schema

```mermaid
erDiagram
    FACT_SALES ||--o{ DIM_CUSTOMER : "customer_sk"
    FACT_SALES ||--o{ DIM_PRODUCT : "product_sk"
    FACT_SALES ||--o{ DIM_DATE : "date_sk"
    
    FACT_SALES {
        bigint sales_sk
        bigint customer_sk
        bigint product_sk
        bigint date_sk
        int order_id
        int quantity
        decimal unit_price
        decimal total_amount
        varchar order_status
    }
    
    DIM_CUSTOMER {
        bigint customer_sk
        int customer_id
        varchar first_name
        varchar last_name
        varchar email
        varchar city
        varchar country
    }
    
    DIM_PRODUCT {
        bigint product_sk
        int product_id
        varchar product_name
        varchar category
        decimal price
    }
    
    DIM_DATE {
        bigint date_sk
        date date_value
        int year
        int quarter
        int month
    }
```

## Snowflake Schema

```mermaid
erDiagram
    FACT_SALES ||--o{ DIM_CUSTOMER : "customer_sk"
    FACT_SALES ||--o{ DIM_PRODUCT : "product_sk"
    DIM_PRODUCT }|--|| DIM_CATEGORY : "category_id"
    DIM_CUSTOMER }|--|| DIM_LOCATION : "location_id"
    DIM_LOCATION }|--|| DIM_COUNTRY : "country_code"
```

## Incremental ETL Flow

```mermaid
flowchart LR
    A[Source Tables] --> B[Change Detection]
    B --> C{Data Changed?}
    C -->|Yes| D[SCD Processing]
    C -->|No| E[No Changes]
    D --> F[Fact Loading]
    F --> G[Update Watermark]
    G --> H[Complete]
```

## Window Function Patterns

```mermaid
graph TD
    A[Base Query] --> B[ROW_NUMBER]
    A --> C[RANK/DENSE_RANK]
    A --> D[LAG/LEAD]
    A --> E[SUM OVER]
    A --> F[AVG OVER]
    A --> G[NTILE]
    
    B --> H[Pagination]
    C --> I[Top-N Analysis]
    D --> J[Trend Analysis]
    E --> K[Running Totals]
    F --> L[Moving Average]
    G --> M[Bucketing]