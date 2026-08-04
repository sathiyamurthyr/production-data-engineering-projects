# Enterprise Data Platform SRE - Interview Questions

## Table of Contents

1. [Monitoring & Observability](#monitoring--observability)
2. [Alert Management](#alert-management)
3. [Incident Management](#incident-management)
4. [SLO/SLI/SLA](#sloslisla)
5. [Reliability Engineering](#reliability-engineering)
6. [Automation & Self-Healing](#automation--self-healing)
7. [Capacity Planning](#capacity-planning)
8. [Disaster Recovery](#disaster-recovery)
9. [Chaos Engineering](#chaos-engineering)
10. [Data Platform Specific](#data-platform-specific)

---

## Monitoring & Observability

### Beginner Questions

**Q1: What are the four golden signals of monitoring?**
<details>
<summary>Answer</summary>

1. **Latency**: Time taken to serve a request
2. **Traffic**: Demand on your system (requests per second)
3. **Errors**: Rate of failed requests
4. **Saturation**: Resource utilization (CPU, memory, disk)

These signals provide a comprehensive view of system health and performance.
</details>

**Q2: What is the difference between metrics, logs, and traces?**
<details>
<summary>Answer</summary>

- **Metrics**: Numeric measurements over time (e.g., CPU usage, request count)
- **Logs**: Discrete event records with timestamps
- **Traces**: Distributed transaction tracking across services

Together they form the three pillars of observability.
</details>

**Q3: What is Prometheus and how does it work?**
<details>
<summary>Answer</summary>

Prometheus is a time-series database and monitoring system that:
- Pulls metrics from configured endpoints (HTTP pull model)
- Stores metrics with timestamps
- Uses PromQL for querying
- Supports alerting through Alertmanager
- Uses a multi-dimensional data model (metrics + labels)
</details>

### Intermediate Questions

**Q4: Explain RED metrics vs USE metrics.**
<details>
<summary>Answer</summary>

**RED metrics** (for services):
- **Rate**: Requests per second
- **Errors**: Errors per second
- **Duration**: Request latency distribution

**USE metrics** (for resources):
- **Utilization**: Average resource usage (%)
- **Saturation**: Resource queue depth/wait time
- **Errors**: Error count

Use RED for service-level monitoring, USE for infrastructure monitoring.
</details>

**Q5: What is a histogram and summary in Prometheus?**
<details>
<summary>Answer</summary>

**Histogram**:
- Pre-configured buckets (e.g., 0.1s, 0.5s, 1s)
- Counts observations in each bucket
- Can compute quantiles across multiple instances
- Lower memory overhead

**Summary**:
- Calculates quantiles on the client-side
- More precise for individual instances
- Higher memory overhead
- Cannot aggregate across instances

Choose histograms for aggregation, summaries for precise individual metrics.
</details>

**Q6: How do you handle high cardinality in metrics?**
<details>
<summary>Answer</summary>

Strategies:
1. **Label carefully**: Avoid high-cardinality labels (user IDs, request IDs)
2. **Use metrics**: Create separate metrics instead of many label combinations
3. **Aggregate early**: Aggregate metrics before sending to Prometheus
4. **Use exemplars**: Sample high-cardinality data
5. **Structured logging**: Use logs for high-cardinality data
6. **Sampling**: Sample requests for detailed traces
</details>

### Advanced Questions

**Q7: Design a monitoring strategy for a data platform processing 1M events/day.**
<details>
<summary>Answer</summary>

1. **Infrastructure metrics**: CPU, memory, disk, network (USE method)
2. **Pipeline metrics**: Throughput, latency, error rate, backlog size
3. **Streaming metrics**: Consumer lag, messages/sec, partition health
4. **Data quality metrics**: Row counts, null rates, duplicate counts
5. **Business metrics**: Data freshness, completeness, SLA compliance
6. **Golden signals**: Per service/component
7. **SLO tracking**: Availability, latency, throughput SLIs
8. **Alerting**: Smart alerting with deduplication and routing
9. **Visualization**: Grafana dashboards for different stakeholders
10. **Cost metrics**: Storage costs, compute costs, data transfer costs
</details>

**Q8: How do you implement distributed tracing in a data pipeline?**
<details>
<summary>Answer</summary>

1. **Instrumentation**: Add OpenTelemetry SDK to all components
2. **Context propagation**: Pass trace context via message headers
3. **Sampling**: Sample 10-100% of traces based on criticality
4. **Span naming**: Consistent naming (extract, transform, load)
5. **Attributes**: Add relevant attributes (record count, partition, etc.)
6. **Integration**: Connect to Jaeger/Zipkin for visualization
7. **Correlation**: Link traces to logs via trace ID
8. **Performance**: Minimize overhead (< 5% recommended)
</details>

---

## Alert Management

### Beginner Questions

**Q9: What makes a good alert?**
<details>
<summary>Answer</summary>

A good alert is:
- **Actionable**: Requires human intervention
- **Relevant**: Important to the recipient
- **Timely**: Arrives when action can be taken
- **Clear**: Title and description explain the issue
- **Contextual**: Includes runbook links, affected services
- **Prioritized**: Appropriate severity level

Avoid alert storms, false positives, and noise.
</details>

**Q10: What is alert fatigue and how do you prevent it?**
<details>
<summary>Answer</summary>

Alert fatigue occurs when too many alerts desensitize responders.

Prevention strategies:
1. **Deduplication**: Group similar alerts
2. **Suppression**: Suppress alerts during maintenance
3. **Filtering**: Route non-critical alerts to secondary channels
4. **Threshold tuning**: Adjust thresholds based on history
5. **Escalation**: Delay non-urgent alerts
6. **Regular review**: Audit alerts weekly, remove unused ones
7. **Actionability review**: Only keep actionable alerts
</details>

### Intermediate Questions

**Q11: Explain the difference between warning, critical, and info alerts.**
<details>
<summary>Answer</summary>

- **Critical (SEV1)**: Complete outage, immediate action needed
  - Response time: < 5 minutes
  - Page on-call immediately
  
- **Warning (SEV2)**: Major degradation
  - Response time: < 15 minutes
  - Notify team lead
  
- **Info (SEV3/4)**: Minor issues or informational
  - Response time: Hours to days
  - Create ticket, no paging

Define clear criteria for each level.
</details>

**Q12: How do you implement alert routing?**
<details>
<summary>Answer</summary>

1. **Severity-based routing**: SEV1 → on-call, SEV2 → team lead
2. **Service-based routing**: Route to team owning the service
3. **Time-based routing**: Business hours vs after-hours
4. **Escalation policies**: If not acknowledged, escalate
5. **Multi-channel**: Slack, PagerDuty, email, SMS
6. **Runbook linking**: Include runbook URL in alert
7. **Context enrichment**: Add environment, affected services
</details>

### Advanced Questions

**Q13: Design an alert management system for a multi-team data platform.**
<details>
<summary>Answer</summary>

Components:
1. **Alert deduplication**: 5-minute window per service
2. **Team ownership**: Alert → team mapping
3. **Escalation chains**: Team lead → manager → director
4. **Maintenance windows**: Suppress during deployments
5. **Alert grouping**: Group by root cause, not symptom
6. **Dashboard integration**: Link to relevant Grafana dashboard
7. **Runbook integration**: Step-by-step resolution guides
8. **Post-incident automation**: Auto-create incident from alert
9. **Metrics**: Alert volume, MTTR, false positive rate
10. **Self-service**: Teams can configure alerts via UI
</details>

---

## Incident Management

### Beginner Questions

**Q14: What is an incident management process?**
<details>
<summary>Answer</summary>

1. **Detection**: Alert triggered or user reports issue
2. **Triage**: Assess severity, impact, assign commander
3. **Response**: Investigate, identify root cause, implement fix
4. **Resolution**: Confirm fix, validate service restored
5. **Postmortem**: Document timeline, root cause, action items

Key principles:
- Clear severity levels
- Defined response times
- Incident commander for SEV1/SEV2
- Blameless culture
</details>

**Q15: What is the difference between SEV1, SEV2, and SEV3 incidents?**
<details>
<summary>Answer</summary>

| Severity | Definition | Response Time | Example |
|----------|------------|---------------|---------|
| SEV1 | Complete outage | < 5 min | Payment system down, data loss |
| SEV2 | Major degradation | < 15 min | SLA breach, feature unavailable |
| SEV3 | Minor issues | < 1 hour | Workaround available, non-critical |

SEV1/SEV2 require incident commander, SEV3 does not.
</details>

### Intermediate Questions

**Q16: What is a blameless postmortem?**
<details>
<summary>Answer</summary>

A blameless postmortem focuses on:
- **What happened**: Timeline of events
- **Why it happened**: Root cause analysis (5 whys)
- **How to prevent**: Action items and improvements
- **Learning**: Organizational learning, not individual blame

Key principles:
- No finger-pointing
- Focus on systems and processes
- Document everything
- Follow up on action items
- Share learnings organization-wide
</details>

**Q17: How do you measure incident management effectiveness?**
<details>
<summary>Answer</summary>

Key metrics:
- **MTTD** (Mean Time To Detect): Time from failure to alert
- **MTTA** (Mean Time To Acknowledge): Time from alert to acknowledgment
- **MTTR** (Mean Time To Resolve): Time from alert to resolution
- **Incident volume**: Trends over time
- **Severity distribution**: SEV1/SEV2/SEV3 ratio
- **Escalation rate**: How often incidents escalate
- **Postmortem completion**: % of incidents with postmortems
- **Action item completion**: Follow-through rate
</details>

### Advanced Questions

**Q18: Design an incident management system for a global data platform.**
<details>
<summary>Answer</summary>

Requirements:
1. **Multi-timezone support**: Follow-the-sun on-call rotation
2. **Language support**: Multi-language notifications
3. **Severity-based escalation**: Automatic escalation paths
4. **War room**: Dedicated Slack channel per incident
5. **Communication templates**: Pre-defined stakeholder updates
6. **Integration**: Connect to monitoring, chat, paging tools
7. **Timeline tracking**: Automated timeline from logs/metrics
8. **Postmortem automation**: Auto-create postmortem doc
9. **Compliance**: Audit trail for regulated industries
10. **Analytics**: Track MTTR, escalation patterns, team performance
</details>

---

## SLO/SLI/SLA

### Beginner Questions

**Q19: What is the difference between SLI, SLO, and SLA?**
<details>
<summary>Answer</summary>

- **SLI (Service Level Indicator)**: Actual measurement
  - Example: 99.5% availability, 150ms latency

- **SLO (Service Level Objective)**: Target for SLI
  - Example: 99.9% availability target

- **SLA (Service Level Agreement)**: Business commitment
  - Example: 99.9% availability with financial penalties

SLO is the engineering target, SLA is the customer promise.
</details>

**Q20: What is an error budget?**
<details>
<summary>Answer</summary>

Error budget = 100% - SLO target

Example:
- SLO: 99.9% availability
- Error budget: 0.1% = ~43 minutes downtime/month

Error budgets allow:
- Risk management
- Release velocity decisions
- Trade-off discussions
- Engineering vs business alignment

When budget is exhausted: freeze releases, focus on reliability.
</details>

### Intermediate Questions

**Q21: How do you calculate error budget burn rate?**
<details>
<summary>Answer</summary>

Burn rate = (consumed budget / total budget) × 100 / window_days

Example:
- SLO: 99.9% (0.1% error budget)
- Current: 99.5% (0.5% errors)
- Consumed: 0.5% / 0.1% = 5× budget
- Window: 30 days
- Burn rate: 5× / 30 = 0.17× per day

High burn rate alerts warn before budget exhaustion.
</details>

**Q22: What is a multi-window alert?**
<details>
<summary>Answer</summary>

Multi-window alerts use multiple time windows to reduce false positives:

Example:
- Alert if error budget > 10% consumed in 1 hour
- AND error budget > 50% consumed in 6 hours

This prevents:
- Alerting on brief blips (1-hour window)
- Missing slow burns (6-hour window)

Multi-window alerts provide better signal-to-noise ratio.
</details>

### Advanced Questions

**Q23: How do you set SLOs for a data pipeline?**
<details>
<summary>Answer</summary>

Consider:
1. **Business requirements**: Data freshness SLAs (e.g., hourly)
2. **Data volume**: Throughput targets (records/sec)
3. **Quality standards**: Completeness, accuracy targets
4. **User expectations**: Dashboard refresh rates
5. **Dependencies**: Upstream system SLAs

Example SLOs:
- **Availability**: 99.5% of pipelines complete successfully
- **Latency**: 95% of pipelines finish within SLA window
- **Freshness**: 90% of data available within 15 minutes of source
- **Quality**: 99.9% of records pass validation rules
</details>

---

## Reliability Engineering

### Beginner Questions

**Q24: What is circuit breaker pattern?**
<details>
<summary>Answer</summary>

Circuit breaker prevents cascading failures:

**States**:
- **Closed**: Normal operation, count failures
- **Open**: Fail fast, don't attempt calls
- **Half-open**: Allow limited requests to test recovery

**Benefits**:
- Fast failure (no waiting for timeouts)
- Prevents resource exhaustion
- Allows downstream systems to recover
- Provides fallback mechanisms

Use when calling external services or databases.
</details>

**Q25: What is retry with exponential backoff?**
<details>
<summary>Answer</summary>

Retry failed operations with increasing delays:

```
Attempt 1: Immediate
Attempt 2: Wait 1s
Attempt 3: Wait 2s
Attempt 4: Wait 4s
Attempt 5: Wait 8s
Max retries: 5
```

Benefits:
- Reduces load on failing systems
- Allows transient issues to resolve
- Prevents thundering herd

Add jitter to prevent synchronized retries.
</details>

### Intermediate Questions

**Q26: Explain the concept of graceful degradation.**
<details>
<summary>Answer</summary>

Graceful degradation: System continues operating with reduced functionality when components fail.

Examples:
- **Cache miss**: Serve stale data while fetching fresh data
- **Read replica down**: Route reads to primary
- **Feature flag**: Disable non-critical features
- **Rate limiting**: Serve priority requests only

Implementation:
1. Identify critical vs non-critical features
2. Design fallback paths
3. Test degradation scenarios
4. Monitor degradation state
</details>

**Q27: What is bulkhead pattern?**
<details>
<summary>Answer</summary>

Bulkhead isolates failures:

**Example**: Cruise ship bulkheads
- One compartment flooded → ship stays afloat
- Other compartments unaffected

**Software application**:
- Separate thread pools for critical/non-critical operations
- Isolate failure domains
- Resource pools per service/tenant

**Benefits**:
- Prevents cascading failures
- Maintains core functionality
- Better resource management
</details>

### Advanced Questions

**Q28: How do you implement automated remediation?**
<details>
<summary>Answer</summary>

1. **Define conditions**: Error budget < 20%, CPU > 90%, etc.
2. **Create runbooks**: Step-by-step remediation procedures
3. **Implement actions**: Restart, scale, failover, etc.
4. **Safety checks**: Pre/post validation
5. **Cooldown periods**: Prevent rapid cycling
6. **Audit logging**: Track all automated actions
7. **Escalation**: If automated fix fails, escalate to human
8. **Testing**: Test in non-production first
9. **Monitoring**: Track automation success rate

Start simple (restart), progress to complex (failover).
</details>

---

## Capacity Planning

### Beginner Questions

**Q29: What is capacity planning?**
<details>
<summary>Answer</summary>

Capacity planning ensures systems can handle future load:

1. **Collect metrics**: Historical usage patterns
2. **Analyze trends**: Growth rate, seasonal patterns
3. **Forecast needs**: Predict future capacity needs
4. **Plan upgrades**: Timeline and budget
5. **Implement**: Scale resources proactively
6. **Monitor**: Track against forecast

Goal: Scale before hitting limits, avoid over-provisioning.
</details>

**Q30: What is the difference between scaling up and scaling out?**
<details>
<summary>Answer</summary>

**Scaling Up (Vertical)**:
- Increase resources of existing server
- Example: 4 CPU → 8 CPU
- Pros: Simpler, no data partitioning
- Cons: Hardware limits, single point of failure

**Scaling Out (Horizontal)**:
- Add more servers
- Example: 1 server → 3 servers
- Pros: Nearly unlimited, better redundancy
- Cons: More complex, requires load balancing

Modern data platforms prefer scaling out.
</details>

### Intermediate Questions

**Q31: How do you forecast capacity needs?**
<details>
<summary>Answer</summary>

Methods:
1. **Linear regression**: Fit line to historical data
2. **Moving average**: Average of recent periods
3. **Exponential smoothing**: Weight recent data more
4. **ARIMA**: Time series forecasting
5. **Machine learning**: Prophet, LSTM for complex patterns

Process:
1. Collect 3-6 months of historical data
2. Identify trends and seasonality
3. Select appropriate model
4. Validate against held-out data
5. Forecast with confidence intervals
6. Add buffer (20-30%)

Tools: Prometheus + Grafana, Prophet, custom scripts.
</details>

**Q32: What metrics should you monitor for capacity planning?**
<details>
<summary>Answer</summary>

**Infrastructure**:
- CPU utilization (target: 60-70%)
- Memory utilization (target: 70-80%)
- Disk I/O and capacity
- Network bandwidth

**Application**:
- Request rate (RPS)
- Queue depth
- Database connections
- Cache hit rate

**Business**:
- User growth rate
- Data volume growth
- Query volume
- Feature adoption

Track these metrics to predict when to scale.
</details>

### Advanced Questions

**Q33: Design a capacity planning process for a growing data platform.**
<details>
<summary>Answer</summary>

**Process**:
1. **Data collection**: Automated metric collection (Prometheus)
2. **Weekly review**: Capacity team reviews trends
3. **Monthly forecast**: Generate 3-month forecast
4. **Quarterly planning**: Budget and timeline for capacity needs
5. **Alerting**: Alert at 80% utilization
6. **Automation**: Auto-scale where possible
7. **Cost optimization**: Right-size resources, use spot instances

**Tools**:
- Prometheus + Grafana for monitoring
- Custom forecasting scripts (Python/R)
- Cost tracking (AWS Cost Explorer, etc.)
- Capacity management tools

**Stakeholders**:
- SRE team: Monitoring and alerting
- Finance: Budget approval
- Engineering: Implementation
</details>

---

## Disaster Recovery

### Beginner Questions

**Q34: What is RPO and RTO?**
<details>
<summary>Answer</summary>

**RPO (Recovery Point Objective)**:
- Maximum acceptable data loss
- How far back to recover
- Example: RPO = 15 min → max 15 min data loss

**RTO (Recovery Time Objective)**:
- Maximum acceptable downtime
- How long to recover
- Example: RTO = 1 hour → system down max 1 hour

Lower RPO/RTO = higher cost.
</details>

**Q35: What are the main backup strategies?**
<details>
<summary>Answer</summary>

**Full Backup**:
- Complete copy of all data
- Pros: Simple, fast restore
- Cons: Time-consuming, storage-heavy

**Incremental Backup**:
- Only changes since last backup
- Pros: Fast backup, less storage
- Cons: Slower restore (need all increments)

**Differential Backup**:
- Changes since last full backup
- Pros: Faster restore than incremental
- Cons: Larger than incremental

**Continuous Backup**:
- Real-time replication (WAL, CDC)
- Pros: Minimal data loss
- Cons: Complex, expensive
</details>

### Intermediate Questions

**Q36: What is the difference between backup and disaster recovery?**
<details>
<summary>Answer</summary>

**Backup**:
- Copying data to prevent loss
- Focus: Data preservation
- Strategy: What to backup, how often, retention

**Disaster Recovery**:
- Restoring operations after disaster
- Focus: System recovery
- Strategy: Failover, RTO/RPO, DR site

Backup is a component of DR. DR includes:
- Infrastructure
- Applications
- Data
- Processes
- People
</details>

**Q37: How do you test disaster recovery plans?**
<details>
<summary>Answer</summary>

Testing methods:
1. **Paper test**: Walk through procedures (low cost)
2. **Simulation**: Test in isolated environment
3. **Parallel test**: Run DR site alongside production
4. **Full interruption**: Actually failover (risky)

Best practices:
- Test quarterly minimum
- Document RTO/RPO achievements
- Update runbooks based on findings
- Involve entire on-call team
- Test different failure scenarios
- Automate where possible

Start with paper tests, progress to full interruptions.
</details>

### Advanced Questions

**Q38: Design a multi-region disaster recovery strategy.**
<details>
<summary>Answer</summary>

**Architecture**:
- **Primary region**: Active-active or active-passive
- **Secondary region**: Warm standby (6-12 hours behind)
- **Tertiary region**: Cold standby (backups only)

**Replication**:
- **Database**: Async replication (30s lag)
- **Object storage**: Cross-region replication
- **Config**: GitOps, automatic sync

**Failover**:
- **Automated health checks**: Every 30s
- **Manual approval**: Required for SEV1 failover
- **DNS failover**: Route53, CloudFlare
- **Data validation**: Verify consistency after failover

**Testing**:
- Quarterly DR drills
- Game days for disaster scenarios
- Chaos engineering for failure simulation

**Cost optimization**:
- Spot instances in DR region
- Scale down non-critical services
- Archive old data to cheaper storage
</details>

---

## Chaos Engineering

### Beginner Questions

**Q39: What is chaos engineering?**
<details>
<summary>Answer</summary>

Chaos engineering: Experimentally testing system resilience by injecting failures.

**Principles**:
1. Build hypothesis about steady state
2. Introduce real-world failures
3. Observe system behavior
4. Improve based on findings

**Example experiments**:
- Kill a Kafka broker
- Inject latency
- Exhaust connection pool
- Fail database primary

**Benefits**:
- Find weaknesses before production
- Build confidence in system
- Improve incident response
- Learn system behavior
</details>

**Q40: What are the risks of chaos engineering?**
<details>
<summary>Answer</summary>

Risks:
1. **Customer impact**: Tests in production affect users
2. **Data corruption**: Failures cause data issues
3. **Cascading failures**: Small failure becomes big outage
4. **Resource exhaustion**: Tests consume resources

Mitigations:
1. **Start small**: Non-production first
2. **Blast radius**: Limit scope (single service, region)
3. **Safety checks**: Pre-flight validation
4. **Rollback plans**: Automated rollback
5. **Monitoring**: Watch for unexpected behavior
6. **Communication**: Inform stakeholders
7. **Stop conditions**: Define exit criteria
</details>

### Intermediate Questions

**Q41: How do you design a chaos experiment?**
<details>
<summary>Answer</summary>

1. **Define hypothesis**:
   - "Killing one Kafka broker won't affect consumer lag > 1000"

2. **Define scope**:
   - Which component (Kafka broker-3)
   - Duration (5 minutes)
   - Blast radius (single topic)

3. **Success criteria**:
   - Consumer lag < 1000
   - No data loss
   - Producers auto-recover

4. **Safety checks**:
   - All brokers healthy
   - Low consumer lag before test
   - During maintenance window

5. **Execute**:
   - Kill broker
   - Monitor metrics
   - Document behavior

6. **Analyze**:
   - Did system behave as expected?
   - What improved/worsened?
   - Action items
</details>

**Q42: What is the difference between chaos engineering and testing?**
<details>
<summary>Answer</summary>

**Testing**:
- Known inputs, expected outputs
- Validates correctness
- Runs in CI/CD
- Controlled environment

**Chaos Engineering**:
- Unknown system behavior
- Tests resilience
- Runs in production-like env
- Realistic failures

Complementary:
- Testing ensures features work
- Chaos ensures system survives failures
- Both needed for reliability
</details>

---

## Data Platform Specific

### Beginner Questions

**Q43: What are the key metrics for data pipelines?**
<details>
<summary>Answer</summary>

**Execution metrics**:
- Success rate (% successful runs)
- Execution time (actual vs expected)
- Records processed (input/output counts)
- Error count and types

**Freshness metrics**:
- Data lag (time since last successful run)
- SLA compliance (% within SLA window)
- Wait time (time spent waiting)

**Quality metrics**:
- Row count changes (sudden drops)
- Null rate
- Duplicate count
- Validation pass rate

**Resource metrics**:
- CPU/memory usage
- Spark executor utilization
- Database connection pool usage
- Storage growth
</details>

**Q44: What is data freshness and why does it matter?**
<details>
<summary>Answer</summary>

Data freshness: Time between data creation and availability for use.

**Why it matters**:
- **Decision making**: Stale data → bad decisions
- **Customer experience**: Real-time dashboards need fresh data
- **Compliance**: Regulations may require freshness (e.g., fraud detection)
- **Competitiveness**: Real-time analytics advantage

**SLO example**:
- 95% of data available within 15 minutes
- RPO: 15 minutes
- Monitor: Alert if data > 30 minutes stale

**Monitoring**:
- Track pipeline completion time
- Monitor source system latency
- Alert on freshness SLA breaches
</details>

### Intermediate Questions

**Q45: How do you monitor streaming data pipelines?**
<details>
<summary>Answer</summary>

**Kafka metrics**:
- **Consumer lag**: Messages consumer is behind
- **Messages in/out**: Throughput
- **Partition count**: Topic distribution
- **Broker health**: Active controllers, disk usage

**Stream processing metrics**:
- **Records/sec**: Processing rate
- **Processing time**: End-to-end latency
- **State size**: State store size
- **Checkpoint duration**: Recovery time

**Monitoring setup**:
1. Kafka broker metrics (JMX)
2. Consumer group metrics (lag)
3. Stream processor metrics (Flink/Spark)
4. End-to-end latency tracing
5. Alerting thresholds (lag > 10k messages)

**Tools**: Prometheus JMX exporter, Burrow for lag monitoring
</details>

**Q46: What is data contract testing?**
<details>
<summary>Answer</summary>

Data contract: Agreement between data producers and consumers.

**Testing**:
1. **Schema validation**: Column names, types
2. **Volume tests**: Row count within expected range
3. **Quality tests**: Null rates, uniqueness
4. **Freshness tests**: Data updated within SLA
5. **Distribution tests**: Value distributions stable

**Implementation**:
- dbt tests for transformations
- Great Expectations for data quality
- Contract validation in CI/CD
- Break glass process for breaking changes

**Benefits**:
- Catch breaking changes early
- Document expectations
- Enable independent teams
- Reduce production incidents
</details>

### Advanced Questions

**Q47: Design an SRE approach for a real-time data platform.**
<details>
<summary>Answer</summary>

**Monitoring**:
- End-to-end latency (P50, P95, P99)
- Throughput (events/sec)
- Error rates (deserialization failures)
- Consumer lag (Kafka)
- Checkpoint health (Flink)

**Alerting**:
- Latency SLA breach (> 1 min P99)
- Consumer lag > 100k messages
- Error rate > 1%
- Checkpoint failures
- Data quality violations

**Automation**:
- Auto-scale stream processors
- Auto-restart failed jobs
- Auto-rebalance partitions
- Auto-fix data quality issues (quarantine)

**Reliability**:
- SLOs: 99.9% availability, < 30s latency
- Error budgets for releases
- Chaos testing for resilience
- Disaster recovery (multi-region)

**Runbooks**:
- Kafka broker failure
- Stream processor failure
- Data quality incident
- State store corruption
</details>

---

## System Design

### Q48: Design a monitoring system for a data platform

**Requirements**:
- Monitor 1000+ data pipelines
- Track metrics from Airflow, Kafka, Spark
- Alert on SLO breaches
- Dashboard for executives and engineers
- Cost < $5000/month

**Solution**:

1. **Metrics Collection**:
   - Prometheus for pull-based metrics
   - StatsD for custom metrics
   - OpenTelemetry for distributed tracing

2. **Storage**:
   - Prometheus TSDB (30 days hot)
   - S3 for long-term storage
   - PostgreSQL for metadata

3. **Alerting**:
   - Prometheus Alertmanager
   - Deduplication and routing
   - PagerDuty integration

4. **Visualization**:
   - Grafana dashboards
   - Executive summary dashboard
   - Pipeline-specific dashboards

5. **Scaling**:
   - Prometheus federation
   - Thanos for long-term storage
   - Grafana for multi-datasource

**Cost breakdown**:
- Infrastructure: $2000/month
- SaaS tools: $1500/month
- Personnel: $1500/month
</details>

---

## Coding Questions

### Q49: Implement a metrics aggregator

```python
class MetricsAggregator:
    """Aggregate metrics from multiple sources."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record(self, name: str, value: float, labels: dict = None):
        """Record metric."""
        key = self._make_key(name, labels)
        self.metrics[key].append(value)
    
    def get_stats(self, name: str, labels: dict = None) -> dict:
        """Get statistics for metric."""
        key = self._make_key(name, labels)
        values = self.metrics.get(key, [])
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
    
    def _make_key(self, name: str, labels: dict) -> str:
        """Create key from name and labels."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}[{label_str}]"
        return name
```

### Q50: Implement a circuit breaker

```python
class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        """Call function with circuit breaker."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset."""
        return time.time() - self.last_failure_time > self.timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass
```

---

## Behavioral Questions

### Q51: Tell me about a time you improved system reliability

**STAR Method**:
- **Situation**: Payment system had 99.5% availability (target: 99.9%)
- **Task**: Improve reliability to meet SLO
- **Action**: 
  - Added circuit breakers to external calls
  - Implemented retry with exponential backoff
  - Added health checks and auto-restart
  - Improved monitoring and alerting
- **Result**: Achieved 99.95% availability, reduced MTTR by 60%

### Q52: How do you handle production incidents under pressure?

**Approach**:
1. **Stay calm**: Focus on resolution, not blame
2. **Assess**: Determine severity and impact
3. **Communicate**: Notify stakeholders
4. **Mitigate**: Restore service quickly (temporary fix)
5. **Investigate**: Find root cause
6. **Fix**: Permanent solution
7. **Document**: Postmortem with action items
8. **Follow-up**: Complete action items, prevent recurrence

### Q53: Describe a time you prevented a production outage

**Example**:
- Noticed error budget burn rate 10× normal
- Investigated and found memory leak in new feature
- Rolled back feature before hitting budget limit
- Added memory profiling to CI/CD
- Presented learnings in all-hands

---

## Quick Reference

### Golden Signals
- Latency, Traffic, Errors, Saturation

### RED Metrics
- Rate, Errors, Duration

### USE Metrics
- Utilization, Saturation, Errors

### SLO Formula
- Error Budget = 100% - SLO Target

### Incident Severity
- SEV1: < 5 min response (outage)
- SEV2: < 15 min response (degraded)
- SEV3: < 1 hour response (minor)
- SEV4: < 24 hours (low impact)

### MTTR Components
- MTTA + MTTR = Total incident time

### RPO/RTO
- RPO: Data loss tolerance
- RTO: Downtime tolerance

---

## Resources

- [Google SRE Book](https://sre.google/sre-book/)
- [Site Reliability Engineering Workbook](https://sre.google/workbook/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Chaos Engineering](https://principlesofchaos.org/)

---

**Note**: These questions cover SRE fundamentals and data platform specifics. Always consider the specific context of the role and company when preparing for interviews.