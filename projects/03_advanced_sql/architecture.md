# Architecture - Advanced SQL Query Optimization

## Query Optimizer Pipeline

```mermaid
flowchart LR
    A[SQL Query] --> B[Parser]
    B --> C[Rewriter]
    C --> D[Planner]
    D --> E[Cost Estimator]
    E --> F[Plan Generator]
    F --> G[Executor]
    
    H[Statistics] --> E
    I[Indexes] --> E
    J[Constraints] --> E
    K[Row Counts] --> E
```

## Join Algorithm Selection

```mermaid
graph TD
    A[Table Sizes] --> B{Size Comparison}
    B -->|Small| C[Nested Loop Join]
    B -->|Large| D{Join Type}
    D -->|Equality| E[Hash Join]
    D -->|Sorted| F[Merge Join]
    D -->|Mixed| G[Hybrid Join]
```

## Partition Pruning Strategy

```mermaid
flowchart LR
    A[Query Filter] --> B{Partition Key}
    B -->|Match| C[Scan Single Partition]
    B -->|Range| D[Scan Multiple Partitions]
    B -->|No Match| E[Full Scan]
```

## Memory Optimization Flow

```mermaid
graph TD
    A[Query Memory] --> B{Memory Available}
    B -->|Sufficient| C[In-Memory Execution]
    B -->|Insufficient| D[Spill to Disk]
    D --> E[Temp Files]
    E --> F[Disk-Based Processing]
```

## Optimizer Components

### Cost Based Optimizer (CBO)
- Uses table statistics to estimate costs
- Considers multiple execution plans
- Chooses plan with lowest estimated cost
- Updates statistics regularly

### Index Selection
- B-tree indexes for range queries
- Hash indexes for equality lookups
- GiST indexes for geometric/data search
- BRIN indexes for large sorted tables

### Join Strategies
- **Hash Join**: Build hash table on smaller table
- **Merge Join**: Sort both tables, merge results
- **Nested Loop**: For each row in outer, scan inner

### Partition Pruning
- Range partitioning: Date, numeric ranges
- List partitioning: Categorical values
- Hash partitioning: Even data distribution
- Skip irrelevant partitions at query time