# Pattern Selection Matrix

How to choose the right data engineering pattern for your scenario.

## Decision Matrix

| Business Problem | Recommended Pattern(s) | Category | Key Benefit |
|---|---|---|---|
| Need a unified data architecture with quality layers | Medallion Architecture | Architecture | Bronze/Silver/Gold progressive refinement |
| Processing batch + streaming data together | Lambda Architecture | Architecture | Batch + speed layer for low latency |
| Building event-driven data flows | Kappa Architecture | Architecture | Pure streaming with reprocessing |
| Distributed data ownership across teams | Data Mesh | Architecture | Domain-oriented data products |
| Vendor-lock-in avoidance | Data Fabric | Architecture | Virtualized cross-platform integration |
| Unified batch + streaming with ACID | Lakehouse | Architecture | Single platform for all data types |
| Traditional analytics data warehouse | Warehouse | Architecture | Mature SQL analytics platform |
| Need low-latency joins on small dim tables | Broadcast Join | Spark | Eliminates shuffle on small tables |
| Large table + large table joins | Shuffle Hash/Sort Join | Spark | Partition-based parallel processing |
| Slow-changing dimension management | SCD Type 2 | ETL | Historical tracking with versioning |
| Loading historical data all at once | Full Refresh | Ingestion | Simple but compute-intensive |
| Processing only new/changed data | Incremental Load | Ingestion | Efficient, only processes deltas |
| Tracking database row changes | CDC | Ingestion | Real-time change capture |
| Periodic snapshots of data state | Snapshot | Ingestion | Point-in-time recovery |
| Breaking large loads into chunks | Micro Batch | Ingestion | Balances throughput and latency |
| Real-time event processing | Streaming Ingestion | Ingestion | Sub-second processing latency |
| External system pushes data | Webhook Ingestion | Ingestion | Event-driven, no polling |
| REST API with pagination | API Pagination | Ingestion | Handles large API result sets |
| Scheduled file drops | File Drop | Ingestion | Simple, decoupled ingestion |
| Data quality validation | Data Validation | Quality | Prevents bad data propagation |
| Detect data anomalies | Anomaly Detection | Quality | Statistical outlier detection |
| Monitor data quality over time | Data Quality Monitoring | Quality | Automated quality checks |
| Verify data consistency | Data Reconciliation | Quality | Cross-system data verification |
| Enforce table relationships | Referential Integrity | Quality | Foreign key constraint enforcement |
| Real-time processing guarantees | Exactly Once Concepts | Streaming | Zero data loss/duplication |
| At-least-once delivery | At-Least-Once Concepts | Streaming | At least one message delivery |
| Late-arriving event handling | Watermark Pattern | Streaming | Defines event-time lateness tolerance |
| Time-slice aggregations | Windowing Pattern | Streaming | Fixed/time/sliding windows |
| Failed message handling | Dead Letter Queue | Streaming | Quarantine problematic messages |
| Re-process historical stream | Replay Pattern | Streaming | Event log reprocessing |
| Control data flow rate | Backpressure | Streaming | Prevents downstream overload |
| Stateful stream processing | State Store | Streaming | Persistent state across batches |
| Join streams together | Streaming Join | Streaming | Event-stream correlation |
| Handle schema changes in stream | Schema Registry Concepts | Kafka | Schema evolution & compatibility |
| Guarantee message ordering | CDC with Ordering | CDC | Ordered event processing |
| Merge data into Delta tables | MERGE Pattern | Delta | Upsert with delta merge |
| Reduce Delta table file count | OPTIMIZE Pattern | Delta | Compacts small files |
| Clean up old Delta data | VACUUM Pattern | Delta | Removes stale file versions |
| Query historical data versions | Time Travel Pattern | Delta | Version-based data access |
| Serverless file ingestion | Auto Loader | Databricks | Auto-schema inference, scaling |
| Data masking for PII | Data Masking | Security | Dynamic/static data obfuscation |
| Tokenize sensitive data | Tokenization | Security | Reversible tokenization |
| Encrypt data at rest | Encryption (At-Rest) | Security | Transparent data encryption |
| Encrypt data in motion | Encryption (In-Transit) | Security | TLS/SSL transport security |
| Manage API keys/secrets | Secrets Management | Security | Centralized secret storage |
| Detect PII in data | PII Detection | Classification | Automated PII identification |
| Data classification tiers | Data Classification | Classification | Sensitivity level tagging |
| CI/CD for data pipelines | CI/CD Pipeline | DevOps | Automated testing & deployment |
| Infrastructure provisioning | Infrastructure as Code | Platform | Declarative infrastructure |
| Developer self-service | Golden Path | Platform | Standardized project templates |
| Provision data services | Self-Service Provisioning | Platform | Automated service creation |
| Internal developer portal | Internal Developer Platform | Platform | Unified developer experience |
| Error budget tracking | Error Budget | SRE | SLO failure budget consumption |
| Capacity forecasting | Capacity Planning | SRE | Resource demand prediction |
| Automated incident response | Incident Response | SRE | Runbook automation |
| Controlled failure testing | Chaos Engineering | SRE | Resilience testing |
| Cost allocation tracking | Cost Allocation | FinOps | Cloud cost attribution |
| Budget monitoring | Budget Monitoring | FinOps | Spend threshold alerts |
| Cost anomaly detection | Cost Anomaly Detection | FinOps | Unusual spend identification |
| Resource optimization | Resource Right Sizing | FinOps | Over-provisioned resource cleanup |

## Cross-Reference: Pattern Combinations

| Pattern 1 | Pattern 2 | Why They Work Together |
|---|---|---|
| Medallion Architecture | Delta Lake | Delta provides ACID + time travel for medallion layers |
| SCD Type 2 | CDC | CDC captures changes that drive Type 2 dimension updates |
| Broadcast Join | Partitioning | Partition large tables, broadcast small dimension tables |
| Streaming + SCD Type 2 | Watermark | Handle late-arriving changes in Type 2 dimension updates |
| CDC | Dead Letter Queue | Quarantine change events that fail schema validation |
| Feature Store | Model Registry | Features + models versioned together for reproducibility |
| RAG | Vector Search | Embeddings indexed in vector DB for similarity retrieval |
| Data Mesh | Data Catalog | Catalog provides discoverability for mesh data products |
| Governance | Data Quality | Policy engine triggers quality checks on data access |
| Platform | Observability | Platform provides metrics/logs for all data products |
| Terraform | Gitops | IaC + GitOps for infrastructure lifecycle management |

## Quick Selection Guide

1. **Start with Architecture** — Choose your foundational pattern
   (Medallion, Lakehouse, Data Mesh, etc.)

2. **Add Ingestion** — How data enters your system
   (Batch, CDC, Streaming, File Drop)

3. **Apply ETL/ELT** — How data is processed and transformed
   (SCD Type 2, Deduplication, Merge)

4. **Optimize** — Performance patterns
   (Broadcast Join, Partitioning, Caching)

5. **Secure & Govern** — Data protection and compliance
   (Encryption, RBAC, Audit Logging)

6. **Observability** — Monitor and alert
   (Metrics, SLOs, Runbooks)

7. **Deploy & Operate** — Production readiness
   (CI/CD, GitOps, Platform Engineering)
