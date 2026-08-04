# Enterprise Data Fabric - Interview Questions

## Table of Contents

1. [Data Fabric Fundamentals](#data-fabric-fundamentals)
2. [Metadata Management](#metadata-management)
3. [Knowledge Graphs](#knowledge-graphs)
4. [Semantic Layer](#semantic-layer)
5. [Data Governance](#data-governance)
6. [Integration Patterns](#integration-patterns)
7. [Architecture & Design](#architecture--design)
8. [Implementation](#implementation)
9. [Operations](#operations)
10. [Best Practices](#best-practices)

---

## Data Fabric Fundamentals

### 1. What is Data Fabric and how does it differ from Data Mesh?

**Answer:**
Data Fabric is an architecture that connects and integrates data across distributed environments through intelligent metadata, semantic abstraction, and automated governance. Key differences from Data Mesh:

| Aspect | Data Fabric | Data Mesh |
|--------|-------------|-----------|
| **Focus** | Technology-centric integration | Domain-centric decentralization |
| **Architecture** | Centralized metadata layer | Federated domain ownership |
| **Abstraction** | Semantic layer unification | Domain-oriented data products |
| **Governance** | Centralized policy enforcement | Federated with global standards |
| **Best For** | Hybrid/multi-cloud integration | Large organizations with domains |

### 2. What are the core principles of Data Fabric?

**Answer:**
1. **Metadata-Driven Architecture**: Active metadata powers all platform decisions
2. **Intelligent Discovery**: AI-assisted data cataloging and classification
3. **Semantic Integration**: Unified business vocabulary across systems
4. **Policy Automation**: Automated governance through policy-as-code
5. **Hybrid Multi-Cloud**: Seamless integration across cloud providers

### 3. Explain the concept of Active Metadata.

**Answer:**
Active Metadata is metadata that is:
- **Real-time**: Continuously updated from source systems
- **Event-driven**: Changes trigger automated actions
- **Connected**: Linked through knowledge graphs
- **Actionable**: Drives automated governance and optimization
- **Comprehensive**: Includes technical, business, and operational aspects

### 4. What is Metadata-Driven Architecture?

**Answer:**
Metadata-Driven Architecture uses metadata as the primary source of truth for:
- Data discovery and cataloging
- Lineage and impact analysis
- Policy enforcement and governance
- Query optimization and routing
- Security and access control
- Cost attribution and chargeback

---

## Metadata Management

### 5. Describe the three types of metadata in Data Fabric.

**Answer:**

**Technical Metadata:**
- Schema definitions (tables, columns, data types)
- Database and table properties
- Indexes, partitions, constraints
- ETL/ELT pipeline definitions
- APIs and endpoints

**Business Metadata:**
- Business glossary terms
- Data stewards and owners
- Data quality rules and metrics
- KPIs and metric definitions
- Data classifications

**Operational Metadata:**
- Usage statistics and metrics
- Query performance data
- Lineage and dependencies
- Data freshness and SLAs
- Access patterns and audit logs

### 6. What is metadata harvesting and how does it work?

**Answer:**
Metadata harvesting is the automated process of:
1. **Connecting** to source systems (databases, warehouses, streaming platforms)
2. **Extracting** metadata using platform-specific APIs/connectors
3. **Transforming** to common metadata models
4. **Enriching** with business context and lineage
5. **Loading** into central metadata repository
6. **Synchronizing** changes through event-driven updates

### 7. Explain metadata versioning and why it's important.

**Answer:**
Metadata versioning tracks changes over time:
- **Schema Evolution**: Track column additions, type changes, deletions
- **Lineage Changes**: Monitor upstream/downstream dependency updates
- **Policy Updates**: Version governance rules and classifications
- **Business Context**: Maintain history of descriptions, owners, classifications

Benefits:
- Audit trail for compliance
- Rollback capabilities
- Historical analysis
- Change impact assessment

---

## Knowledge Graphs

### 8. What is a Knowledge Graph in the context of Data Fabric?

**Answer:**
A Knowledge Graph is a graph database (typically Neo4j) that:
- **Nodes** represent entities (tables, columns, pipelines, reports, people)
- **Edges** represent relationships (lineage, ownership, similarity, usage)
- **Properties** store attributes (tags, classifications, scores, timestamps)

Benefits:
- Complex relationship queries
- Impact analysis traversals
- Similarity-based recommendations
- Contextual data discovery

### 9. How do you model data lineage in a knowledge graph?

**Answer:**
```cypher
// Create asset nodes
CREATE (source:Asset {id: 'table1', name: 'raw_data'})
CREATE (transform:Asset {id: 'table2', name: 'clean_data'})
CREATE (target:Asset {id: 'table3', name: 'analytics'})

// Create lineage relationships
CREATE (source)-[r:LINEAGE {type: 'batch', timestamp: '2024-01-01'}]->(transform)
CREATE (transform)-[r2:LINEAGE {type: 'batch', timestamp: '2024-01-02'}]->(target)

// Query upstream lineage
MATCH path = (target:Asset {id: 'table3'})<-[:LINEAGE*1..5]-(upstream)
RETURN path
```

### 10. What queries can you perform with a knowledge graph?

**Answer:**
- **Lineage Traversal**: Find all upstream/downstream dependencies
- **Impact Analysis**: Identify affected assets when schema changes
- **Similarity Detection**: Find similar assets based on shared characteristics
- **Path Finding**: Discover shortest paths between entities
- **Community Detection**: Group related assets into domains
- **Recommendations**: Suggest related assets based on usage patterns

---

## Semantic Layer

### 11. What is a Semantic Layer and why is it important?

**Answer:**
A Semantic Layer provides:
- **Business Abstraction**: Maps technical assets to business terms
- **Unified Vocabulary**: Common definitions across the organization
- **Metric Standardization**: Consistent calculation methods
- **Self-Service**: Business users can query without technical knowledge
- **Context Preservation**: Maintains business meaning across systems

### 12. How do you implement a business glossary?

**Answer:**
1. **Define Terms**: Create authoritative business definitions
2. **Map to Assets**: Link glossary terms to technical assets
3. **Categorize**: Organize into domains and hierarchies
4. **Stewardship**: Assign business owners and reviewers
5. **Versioning**: Track definition changes over time
6. **Enrichment**: Auto-suggest mappings using NLP/ML

### 13. Explain the concept of data contracts.

**Answer:**
Data Contracts are formal agreements between data producers and consumers:
- **Schema**: Column names, types, constraints
- **Quality Rules**: Completeness, uniqueness, validity thresholds
- **SLAs**: Freshness, availability, support levels
- **Ownership**: Producer, steward, escalation contacts
- **Versioning**: Semantic versioning for breaking changes
- **Enforcement**: Automated validation in CI/CD pipelines

---

## Data Governance

### 14. What is policy-as-code in Data Fabric?

**Answer:**
Policy-as-code treats governance rules as versioned, automated code:
```yaml
policies:
  - name: "pii_protection"
    description: "PII data must be encrypted"
    rules:
      - condition: "sensitivity in ['PII', 'PHI']"
        actions:
          - ENCRYPT
          - AUDIT
          - MASK
    enabled: true
```

Benefits:
- Version control in Git
- Automated enforcement
- Consistent application
- Audit trail
- Rapid updates

### 15. How do you handle PII detection and classification?

**Answer:**
1. **Pattern Matching**: Regex for SSN, credit cards, emails
2. **Keyword Detection**: Column name analysis (name, email, phone)
3. **Data Profiling**: Sample data analysis for sensitive patterns
4. **Machine Learning**: NLP for context-aware detection
5. **Manual Override**: Data steward annotations
6. **Classification Levels**: PUBLIC, INTERNAL, CONFIDENTIAL, PII, PHI

### 16. Explain data stewardship workflows.

**Answer:**
Data Stewardship involves:
1. **Assignment**: Designate owners for data domains
2. **Review**: Regular data quality and classification reviews
3. **Approval**: Workflow for metadata changes
4. **Escalation**: Process for resolving disputes
5. **Reporting**: Steward performance metrics
6. **Training**: Ongoing education on governance policies

---

## Integration Patterns

### 17. How do you integrate Snowflake with Data Fabric?

**Answer:**
```python
from connectors.snowflake import SnowflakeConnector

connector = SnowflakeConnector({
    "account": "org.account",
    "user": "metadata_user",
    "password": "password",
    "warehouse": "COMPUTE_WH",
    "database": "ANALYTICS",
    "schema": "PUBLIC"
})

# Test connection
if connector.test_connection():
    # Harvest metadata
    assets = connector.get_assets()
    for asset in assets:
        catalog.register_asset(asset)
```

18. **Explain Databricks Unity Catalog integration.**

**Answer:**
Unity Catalog provides:
- **Unified Governance**: Single permission model across workspaces
- **Data Lineage**: Automatic lineage capture
- **Tags and Classifications**: Native metadata management
- **Volume Support**: Managed storage with metadata
- **Function Catalog**: UDF registration and discovery

Integration uses Databricks SDK:
```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(host=url, token=token)
tables = w.tables.list(catalog_name="main", schema_name="default")
```

### 19. How does Kafka metadata harvesting work?

**Answer:**
1. **Topic Discovery**: List all topics via AdminClient
2. **Schema Retrieval**: Fetch from Schema Registry
3. **Partition Info**: Replication factor, partition count
4. **Consumer Groups**: Identify downstream consumers
5. **ACL Analysis**: Access control metadata
6. **Lineage Mapping**: Connect to producers and consumers

### 20. Describe Airflow integration for pipeline metadata.

**Answer:**
Airflow integration captures:
- **DAG Definitions**: Tasks, dependencies, schedules
- **DAG Runs**: Execution history, duration, status
- **Task Instances**: Individual task metadata
- **XCom Data**: Inter-task communication
- **Variables and Connections**: Configuration metadata
- **Lineage**: Data flow between tasks

Uses Airflow REST API:
```python
GET /api/v1/dags/{dag_id}
GET /api/v1/dags/{dag_id}/dagRuns
GET /api/v1/dags/{dag_id}/taskInstances
```

---

## Architecture & Design

### 21. Describe the layered architecture of Data Fabric.

**Answer:**
```
┌─────────────────────────────────────┐
│   Consumption Layer                  │
│   (Analytics, ML, BI, APIs)         │
├─────────────────────────────────────┤
│   Platform Services                  │
│   (Search, Discovery, Catalog)       │
├─────────────────────────────────────┤
│   Governance Layer                   │
│   (Policies, Classification, RBAC)   │
├─────────────────────────────────────┤
│   Knowledge Layer                    │
│   (Graph, Glossary, Semantics)       │
├─────────────────────────────────────┤
│   Metadata Layer                     │
│   (Technical, Business, Operational) │
├─────────────────────────────────────┤
│   Integration Layer                  │
│   (Connectors, Harvesters)           │
└─────────────────────────────────────┘
```

### 22. How do you design for scalability in Data Fabric?

**Answer:**
1. **Horizontal Scaling**: API servers, workers, connectors
2. **Caching Strategy**: Redis for frequent queries
3. **Database Sharding**: Partition metadata by domain
4. **Event-Driven**: Kafka for async operations
5. **Connection Pooling**: Manage DB connections efficiently
6. **Microservices**: Decompose by capability
7. **CDN**: Distribute static assets globally

### 23. What is the role of the semantic layer?

**Answer:**
The Semantic Layer:
- **Decouples** business logic from technical implementation
- **Standardizes** metric definitions across tools
- **Enables** self-service analytics
- **Preserves** business context during migrations
- **Facilitates** data discovery through business terms
- **Supports** multi-lingual and multi-currency scenarios

---

## Implementation

### 24. How do you implement metadata APIs?

**Answer:**
RESTful API design:
```python
# Asset CRUD
POST   /api/v1/assets          # Create asset
GET    /api/v1/assets          # List assets
GET    /api/v1/assets/{urn}    # Get asset
PUT    /api/v1/assets/{urn}    # Update asset
DELETE /api/v1/assets/{urn}    # Delete asset

# Search and Discovery
GET    /api/v1/search?q=query  # Search assets
GET    /api/v1/assets/{urn}/lineage  # Get lineage
GET    /api/v1/discovery/report  # Discovery insights

# Governance
POST   /api/v1/policies/validate  # Validate policies
GET    /api/v1/policies/report    # Compliance report
```

### 25. Explain event-driven metadata updates.

**Answer:**
Events trigger automated metadata updates:
```python
# Schema change event
{
  "type": "schema_change",
  "connector": "snowflake",
  "asset_id": "db.schema.table",
  "changes": [
    {"column": "new_col", "type": "added"},
    {"column": "old_col", "type": "modified"}
  ]
}

# New asset event
{
  "type": "new_asset",
  "connector": "kafka",
  "asset": {...}
}

# Handler
async def handle_schema_change(event):
    asset = connector.get_asset(event["asset_id"])
    catalog.update_asset(asset.urn, {"columns": asset.columns})
```

### 26. How do you ensure metadata quality?

**Answer:**
Quality dimensions:
1. **Completeness**: Required fields populated
2. **Accuracy**: Metadata matches reality
3. **Consistency**: Cross-system alignment
4. **Timeliness**: Freshness within SLA
5. **Validity**: Conforms to schema/rules

Validation:
```python
quality_rules = [
    {"field": "name", "rule": "not_empty"},
    {"field": "platform", "rule": "in_list", "values": ["snowflake", "databricks"]},
    {"field": "quality_score", "rule": "range", "min": 0, "max": 1}
]

for rule in quality_rules:
    validate(asset, rule)
```

---

## Operations

### 27. How do you monitor Data Fabric health?

**Answer:**
Health checks:
```python
# Component health
health.check("database", check_db_connection)
health.check("neo4j", check_neo4j_connection)
health.check("redis", check_redis_connection)
health.check("connectors", check_all_connectors)

# Metrics
metrics.gauge("catalog.total_assets", count)
metrics.counter("harvester.assets_harvested", count)
metrics.histogram("search.query_time_ms", duration)
metrics.gauge("policy.violations", count)
```

Dashboards:
- Asset growth trends
- Harvest success rates
- Search query performance
- Policy violation trends
- Connector health status

### 28. Describe a typical deployment strategy.

**Answer:**
1. **Blue-Green Deployment**: Zero-d downtime updates
2. **Canary Releases**: Test with subset of users
3. **Feature Flags**: Gradual feature rollout
4. **Rollback Plan**: Automated rollback on failure
5. **Database Migrations**: Backward-compatible schema changes
6. **Monitoring**: Real-time health and performance metrics

CI/CD pipeline:
```yaml
stages:
  - test: Unit, integration, contract tests
  - build: Docker image, push to registry
  - deploy_staging: Deploy to staging environment
  - integration_test: Run integration tests
  - approve: Manual approval for production
  - deploy_prod: Rolling update to production
  - verify: Smoke tests and health checks
```

### 29. How do you handle disaster recovery?

**Answer:**
1. **Database Backups**: Daily PostgreSQL dumps, Neo4j exports
2. **Replication**: Multi-region database replication
3. **Cache Warm-up**: Pre-load Redis from backup
4. **Monitoring**: Automated failover detection
5. **Runbooks**: Documented recovery procedures
6. **Testing**: Regular DR drills

RTO: < 1 hour
RPO: < 24 hours

---

## Best Practices

### 30. What are common Data Fabric anti-patterns?

**Answer:**
❌ **Anti-patterns**:
1. **Metadata Silos**: Separate catalogs per system
2. **Manual Processes**: Spreadsheet-based governance
3. **Over-Engineering**: Building before understanding requirements
4. **Ignoring Lineage**: Not tracking data provenance
5. **Weak Governance**: No automated policy enforcement
6. **Poor Documentation**: Outdated or missing docs

✅ **Best Practices**:
1. **Centralized Metadata**: Single source of truth
2. **Automation First**: Reduce manual overhead
3. **Incremental Delivery**: Start small, expand gradually
4. **Lineage by Design**: Track from day one
5. **Policy as Code**: Automated enforcement
6. **Living Documentation**: Auto-generated from metadata

---

## Scenario-Based Questions

### 31. A business user needs to find all customer data. How do you help them?

**Answer:**
1. **Search**: Use semantic search for "customer"
2. **Glossary**: Show business terms related to customer
3. **Facets**: Filter by platform, domain, sensitivity
4. **Recommendations**: Suggest related assets
5. **Lineage**: Show data flow and transformations
6. **Quality**: Display quality scores and certifications
7. **Ownership**: Provide contact for data steward

### 32. How do you handle a schema change in production?

**Answer:**
1. **Detection**: Connector detects schema change via event
2. **Validation**: Check against data contract
3. **Impact Analysis**: Find downstream dependencies
4. **Notification**: Alert data owners and consumers
5. **Approval**: Get sign-off from stewards
6. **Update**: Modify metadata and lineage
7. **Propagate**: Notify all affected systems
8. **Monitor**: Track usage and issues

### 33. Describe how you'd implement data quality monitoring.

**Answer:**
```python
quality_checks = {
    "completeness": {
        "column": "customer_id",
        "rule": "not_null",
        "threshold": 0.99
    },
    "uniqueness": {
        "column": "email",
        "rule": "unique",
        "threshold": 1.0
    },
    "validity": {
        "column": "status",
        "rule": "in_set",
        "values": ["active", "inactive"],
        "threshold": 0.95
    }
}

# Run checks
for check in quality_checks:
    result = execute_check(check)
    metrics.record("data_quality", result.score)
    
    if result.score < check.threshold:
        alert_data_steward(check, result)
```

### 34. How do you ensure compliance with GDPR?

**Answer:**
1. **PII Discovery**: Automated sensitive data detection
2. **Classification**: Tag all PII assets
3. **Lineage Tracking**: Understand data flow
4. **Access Control**: Implement RBAC/ABAC
5. **Audit Logging**: Track all access and modifications
6. **Right to Erasure**: Track PII for deletion
7. **Data Portability**: Export capabilities
8. **Consent Management**: Track user consent status

### 35. Design a data product certification process.

**Answer:**
1. **Submission**: Owner submits asset for certification
2. **Automated Checks**:
   - Quality score > 90%
   - Complete documentation
   - No critical policy violations
   - Fresh data (updated within 24h)
3. **Manual Review**:
   - Business steward approval
   - Security review for sensitive data
   - Architecture review for scalability
4. **Certification**: Add certification tag, update catalog
5. **Monitoring**: Ongoing quality checks
6. **Renewal**: Quarterly re-certification

---

## Technical Deep Dive

### 36. How does search indexing work in Data Fabric?

**Answer:**
1. **Tokenization**: Extract tokens from name, description, tags
2. **Normalization**: Lowercase, remove special chars
3. **Inverted Index**: Map tokens to assets
4. **Scoring**: TF-IDF or BM25 ranking
5. **Faceting**: Aggregate by platform, type, domain
6. **Autocomplete**: Prefix matching on tokens
7. **Synonyms**: Business term mappings

### 37. Explain the metadata harvesting workflow.

**Answer:**
```
1. Scheduler triggers harvest
2. Connector connects to source system
3. Extract metadata (tables, schemas, etc.)
4. Transform to common Asset model
5. Enrich with additional metadata
6. Compare with existing catalog
7. Detect changes (new, updated, deleted)
8. Update catalog and knowledge graph
9. Trigger events for changes
10. Log harvest statistics
```

### 38. How do you handle cross-platform lineage?

**Answer:**
1. **Normalization**: Convert platform-specific lineage to common format
2. **Mapping**: Map platform assets to canonical URNs
3. **Joining**: Link lineage across system boundaries
4. **Validation**: Ensure consistency and completeness
5. **Visualization**: Render unified lineage graph
6. **Querying**: Support cross-platform traversal

Example:
```
Snowflake (raw_data) 
  → ADF (copy_to_blob) 
    → Databricks (transform) 
      → Snowflake (analytics)
```

### 39. Describe the policy evaluation engine.

**Answer:**
```python
class PolicyEngine:
    def evaluate_asset(self, asset):
        violations = []
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            for rule in policy.rules:
                if self.evaluate_condition(rule.condition, asset):
                    violation = PolicyViolation(
                        policy_id=policy.id,
                        asset_id=asset.id,
                        rule=rule.name,
                        action=rule.action
                    )
                    violations.append(violation)
        
        return violations
```

### 40. How do you implement automated data classification?

**Answer:**
```python
class AutoClassifier:
    def classify(self, asset):
        # Check column names
        pii_columns = self.detect_pii_columns(asset.columns)
        phi_columns = self.detect_phi_columns(asset.columns)
        
        # Check data samples
        data_sample = self.get_sample_data(asset)
        pii_patterns = self.regex_patterns.findall(data_sample)
        
        # Calculate confidence
        confidence = self.calculate_confidence(
            pii_columns, phi_columns, pii_patterns
        )
        
        # Determine classification
        if phi_columns:
            return SensitivityLevel.PHI, confidence
        elif pii_columns:
            return SensitivityLevel.PII, confidence
        else:
            return SensitivityLevel.INTERNAL, confidence
```

---

## Advanced Topics

### 41. Explain the concept of data contracts.

**Answer:**
Data Contracts formalize producer-consumer agreements:
- **Schema Versioning**: Semantic versioning for breaking changes
- **Quality SLAs**: Freshness, completeness, accuracy
- **Change Management**: Notification and deprecation policies
- **Support**: Owner contacts and escalation paths
- **Monitoring**: Real-time SLA tracking
- **Enforcement**: Automated validation in CI/CD

### 42. How do you implement data mesh principles in Data Fabric?

**Answer:**
1. **Domain Ownership**: Each domain owns their metadata
2. **Federated Governance**: Global standards, local enforcement
3. **Self-Service**: Domain teams can publish assets
4. **Product Thinking**: Data as a product mindset
5. **Infrastructure**: Shared platform capabilities
6. **Policies**: Automated cross-domain validation

### 43. Describe multi-cloud metadata synchronization.

**Answer:**
Challenges:
- Different metadata models per cloud
- Network latency and reliability
- Consistency across regions
- Security and compliance

Solutions:
- Canonical metadata model
- Event-driven synchronization
- Conflict resolution strategies
- Regional caching
- Encrypted communication

### 44. How do you measure Data Fabric ROI?

**Answer:**
Metrics:
1. **Time to Data**: Reduced search and discovery time
2. **Data Quality**: Fewer errors, higher trust
3. **Compliance**: Reduced audit failures
4. **Self-Service**: Reduced IT backlog
5. **Cost Savings**: Eliminated redundant tools
6. **Adoption**: User engagement metrics

Calculation:
```
ROI = (Benefits - Costs) / Costs
Benefits = Time savings + Error reduction + Compliance avoidance
```

### 45. What's the future of Data Fabric?

**Answer:**
Trends:
1. **AI-Augmented**: ML for automated metadata enrichment
2. **Real-Time**: Streaming metadata updates
3. **Graph Native**: Knowledge graphs as primary store
4. **Composable**: Modular, API-first architecture
5. **Edge Integration**: IoT and edge device metadata
6. **Quantum-Ready**: Future-proofing for quantum computing

---

## Quick Reference

### Key Terms
- **Active Metadata**: Real-time, event-driven metadata
- **Knowledge Graph**: Graph database for relationships
- **Semantic Layer**: Business abstraction over technical assets
- **Lineage**: Data provenance and dependencies
- **Data Contract**: Formal agreement between producers/consumers
- **Policy-as-Code**: Versioned, automated governance

### Common Acronyms
- **PII**: Personally Identifiable Information
- **PHI**: Protected Health Information
- **RBAC**: Role-Based Access Control
- **ABAC**: Attribute-Based Access Control
- **SLA**: Service Level Agreement
- **CDC**: Change Data Capture
- **ETL/ELT**: Extract, Transform, Load

### Essential Tools
- **Metadata**: OpenMetadata, DataHub, Apache Atlas
- **Graph DB**: Neo4j, Amazon Neptune
- **Search**: Elasticsearch, OpenSearch
- **Quality**: Great Expectations, Soda
- **Orchestration**: Airflow, Prefect, Dagster
- **Streaming**: Kafka, Pulsar