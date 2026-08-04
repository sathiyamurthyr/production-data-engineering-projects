# Enterprise Data Platform SRE

Production-ready Site Reliability Engineering (SRE) platform for enterprise data platforms.

## Overview

This project implements a comprehensive SRE framework specifically designed for enterprise data platforms, combining industry-standard SRE practices with data platform-specific requirements.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Platform Layer                       │
│  Pipelines │ Streaming │ AI/ML │ Warehouses │ Data Products │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Observability Layer                         │
│  Metrics │ Logs │ Traces │ Events                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SRE Platform Layer                         │
│                                                               │
│  Monitoring │ Alerting │ Incident │ Reliability │ Automation │
│  Capacity   │ DR       │ Chaos     │ Runbooks    │ Dashboards │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                        │
│  Kubernetes │ Cloud │ Network │ Storage │ Security          │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Monitoring & Metrics

**Location:** `monitoring/metrics/`

- **MetricsCollector**: Collect and aggregate platform metrics
- **GoldenSignalsCollector**: Track latency, traffic, errors, saturation
- **SLITracker**: Service Level Indicator monitoring
- **ErrorBudgetManager**: Error budget tracking and management

**Key Metrics:**
- Pipeline execution metrics (success rate, latency, throughput)
- Streaming metrics (consumer lag, messages/sec, partitions)
- Infrastructure metrics (CPU, memory, disk I/O, network)
- AI platform metrics (inference latency, token usage, cost)

### 2. Alert Management

**Location:** `monitoring/alerts/`

- **AlertManager**: Central alert management
- **AlertDeduplicator**: Reduce alert noise
- **AlertRouter**: Route alerts to appropriate channels
- **AlertEnrichment**: Add context to alerts
- **AlertAggregator**: Group related alerts

**Features:**
- Severity-based routing (SEV1-SEV4)
- Deduplication windows
- Runbook integration
- Escalation policies

### 3. Incident Management

**Location:** `incident/`

- **IncidentManager**: Full incident lifecycle management
- **IncidentTimeline**: Track incident events
- **PostmortemManager**: Automated postmortem creation
- **IncidentAnalyzer**: Pattern analysis and reporting

**Severity Levels:**
- SEV1: Complete outage (< 5 min response)
- SEV2: Major degradation (< 15 min response)
- SEV3: Minor issues (< 1 hour response)
- SEV4: Low impact (< 24 hour response)

### 4. Reliability Engineering

**Location:** `reliability/`

- **SLOManager**: Service Level Objective management
- **ReliabilityEngineer**: Automated remediation
- **ErrorBudgetManager**: Error budget tracking

**SLO Features:**
- Define SLOs with rolling windows
- Error budget calculation
- Burn rate monitoring
- Automated remediation triggers

### 5. Automation & Self-Healing

**Location:** `automation/`

- **AutoHealer**: Automated issue resolution
- **SelfHealingPipeline**: Pipeline-specific healing
- **HealthChecker**: Component health monitoring

**Healing Actions:**
- Service restart
- Scale up/down
- Failover
- Cache clearing
- Circuit breaker management

### 6. Capacity Planning

**Location:** `capacity/`

- **CapacityPlanner**: Forecast capacity needs
- **CapacityOptimizer**: Resource optimization
- **CostAnalyzer**: Cost tracking and optimization

**Features:**
- Load forecasting (linear regression, ARIMA)
- Scaling recommendations
- Cost analysis and trends
- Resource optimization

### 7. Disaster Recovery

**Location:** `dr/`

- **BackupManager**: Backup scheduling and management
- **RecoveryEngine**: Execute recovery procedures
- **FailoverCoordinator**: Multi-region failover
- **RecoveryTimeEstimator**: RTO/RPO estimation

**DR Features:**
- Automated backup scheduling
- Recovery point management
- Failover orchestration
- Recovery validation

### 8. Chaos Engineering

**Location:** `chaos/`

- **ChaosEngine**: Execute chaos experiments
- **ChaosValidator**: Validate experiment results

**Scenarios:**
- Kafka broker failure
- Database connection exhaustion
- High latency injection
- Pipeline failure simulation

### 9. Runbooks

**Location:** `runbooks/`

- **RunbookLibrary**: Operational runbook management
- **IncidentResponseProcedure**: Standard response procedures
- **EmergencyContacts**: Contact management

**Default Runbooks:**
- Kafka broker failure
- Airflow scheduler failure
- Data pipeline failure
- High latency investigation
- Data quality incidents

### 10. Dashboards

**Location:** `monitoring/dashboards/`

- **Platform Health Dashboard**: Golden signals, pipeline metrics, infrastructure

## Project Structure

```
projects/25_enterprise_data_platform_sre/
├── README.md
├── architecture.md
├── requirements.txt
├── monitoring/
│   ├── metrics/
│   │   └── collector.py
│   ├── alerts/
│   │   └── alert_manager.py
│   └── dashboards/
│       └── platform_health.json
├── incident/
│   └── manager.py
├── reliability/
│   └── slo.py
├── automation/
│   └── auto_healer.py
├── capacity/
│   └── forecaster.py
├── dr/
│   └── backup_manager.py
├── chaos/
│   └── chaos_engine.py
├── runbooks/
│   └── incident_response.py
└── tests/
    └── (test files)
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Example

```python
from monitoring.metrics.collector import MetricsCollector, GoldenSignalsCollector
from incident.manager import IncidentManager
from reliability.slo import SLOManager

# Initialize components
metrics = MetricsCollector()
incident_mgr = IncidentManager()
slo_mgr = SLOManager()

# Record metrics
metrics.record_pipeline_metrics(
    pipeline_id="pipeline-001",
    success=True,
    latency_ms=1500,
    records_processed=10000
)

# Define SLO
slo_mgr.define_slo(
    slo_id="pipeline-availability",
    name="Pipeline Availability",
    description="Pipeline success rate",
    metric_query="avg(pipeline_success) * 100",
    target=99.5,
    window_days=30
)

# Check compliance
compliance = slo_mgr.check_compliance("pipeline-availability", 99.8)
print(f"SLO Compliant: {compliance.compliant}")

# Create incident if needed
if not compliance.compliant:
    incident = incident_mgr.create_incident(
        title="Pipeline SLO Breach",
        description="Pipeline success rate below SLO target",
        severity="sev2",
        source="slo_monitor",
        affected_services=["data-pipeline"]
    )
```

### Alert Management

```python
from monitoring.alerts.alert_manager import AlertManager, AlertRule

# Initialize alert manager
alert_mgr = AlertManager()

# Register alert rule
rule = AlertRule(
    rule_id="high-latency",
    name="High Pipeline Latency",
    description="Pipeline latency exceeds threshold",
    expression="pipeline_latency > 5000",
    severity="warning",
    duration=300
)
alert_mgr.register_rule(rule)

# Evaluate alert
alert = alert_mgr.evaluate_alert("high-latency", 6000)
if alert:
    print(f"Alert triggered: {alert.title}")
```

### Self-Healing

```python
from automation.auto_healer import AutoHealer, HealingStrategy

# Initialize auto-healer
healer = AutoHealer()

# Register healing strategy
strategy = HealingStrategy(
    strategy_id="restart-pipeline",
    component="data-pipeline",
    issue_type="pipeline_failure",
    description="Restart failed pipeline",
    action="restart",
    max_attempts=3,
    cooldown_minutes=5
)
healer.register_strategy(strategy)

# Detect and heal issue
issue = healer.detect_issue(
    component="data-pipeline",
    issue_type="pipeline_failure",
    description="Pipeline failed",
    severity="high"
)
```

## Key Concepts

### Golden Signals

The four golden signals of monitoring:
1. **Latency**: Request response time
2. **Traffic**: Requests per second
3. **Errors**: Error rate
4. **Saturation**: Resource utilization

### SLO/SLI/SLA

- **SLI (Service Level Indicator)**: Actual measurement
- **SLO (Service Level Objective)**: Target for SLI
- **SLA (Service Level Agreement)**: Business commitment

### Error Budget

Error budget = 100% - SLO target

Example: 99.9% SLO = 0.1% error budget = ~43 minutes downtime/month

### RED Metrics

For services:
- **Rate**: Requests per second
- **Errors**: Errors per second
- **Duration**: Request latency distribution

### USE Metrics

For resources:
- **Utilization**: Average resource usage
- **Saturation**: Resource queue depth
- **Errors**: Error count

## Best Practices

### Monitoring
- Instrument all critical paths
- Use meaningful metric names
- Implement consistent tagging
- Set appropriate alert thresholds
- Reduce alert noise through deduplication

### Incident Management
- Define clear severity levels
- Establish response time SLAs
- Use incident commanders for SEV1/SEV2
- Document everything in postmortems
- Track action items to completion

### Reliability
- Start with user-facing SLOs
- Track error budgets carefully
- Implement automated remediation
- Practice chaos engineering
- Conduct regular game days

### Automation
- Start with simple healing actions
- Implement circuit breakers
- Use exponential backoff
- Maintain audit logs
- Test in non-production first

### Capacity Planning
- Collect historical metrics
- Use multiple forecasting models
- Plan for peak load + buffer
- Review recommendations monthly
- Automate scaling where possible

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=monitoring --cov=incident --cov=reliability

# Run specific test
pytest tests/test_monitoring.py -v
```

## Integration Examples

### Airflow Integration

```python
from monitoring.metrics.collector import MetricsCollector

metrics = MetricsCollector()

# Record Airflow DAG metrics
metrics.record_pipeline_metrics(
    pipeline_id="dag_id",
    success=True,
    latency_ms=1500,
    records_processed=1000
)
```

### Kafka Integration

```python
# Record streaming metrics
metrics.record_streaming_metrics(
    topic="events",
    consumer_group="processor",
    messages_per_second=5000,
    consumer_lag=100,
    partition_count=12
)
```

### Databricks Integration

```python
# Record infrastructure metrics
metrics.record_infrastructure_metrics(
    component="databricks-cluster",
    cpu_percent=75.0,
    memory_percent=80.0,
    disk_io=50.0,
    network_io=100.0
)
```

## Interview Questions

See `interview-questions.md` for common SRE interview questions.

## Exercises

See `exercises/` directory for hands-on exercises.

## Troubleshooting

See `troubleshooting.md` for common issues and solutions.

## References

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Site Reliability Engineering](https://en.wikipedia.org/wiki/Site_reliability_engineering)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [OpenTelemetry](https://opentelemetry.io/docs/)

## License

MIT License

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.