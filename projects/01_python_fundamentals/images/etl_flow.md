# ETL Flow Diagram

```mermaid
graph LR
    A[Extract CSV/JSON/API] --> B[Transform Data]
    B --> C[Validate Data]
    C --> D[Load to Target]
    D --> E[Log Results]

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#e8f5e9
    style E fill:#fce4ec
```

# Python Execution Flow

```mermaid
flowchart TD
    A[Python Script] --> B[Parse Arguments]
    B --> C[Load Config]
    C --> D[Initialize Logger]
    D --> E[Extract Data]
    E --> F{Data Valid?}
    F -->|Yes| G[Transform Data]
    F -->|No| H[Log Error]
    G --> I[Load Data]
    I --> J[Log Success]
    H --> K[Exit with Error]
    J --> L[Exit Clean]

    style E fill:#bbdefb
    style G fill:#ffccbc
    style I fill:#c8e6c9
```

# Module Relationships

```mermaid
graph TD
    A[main.py] --> B[config.py]
    A --> C[logger.py]
    A --> D[models.py]
    A --> E[examples.py]

    B --> F[.env]
    B --> G[YAML Configs]

    C --> H[stdout]
    C --> I[log files]

    style A fill:#f5f5f5,stroke:#333,stroke-width:2px