# Incident Playbook: Spark Shuffle OOM and Data Skew

## Symptoms
Executors fail with `java.lang.OutOfMemoryError: Java heap space` or `FetchFailedException` during wide transformations (`groupBy`, `join`). Stage progress stalls at 99% on a single straggler task.

## Root Cause Diagnosis
1. Check Spark UI Stages tab for max vs median task duration and shuffle read size.
2. Inspect join keys for NULL values or hot keys (e.g., `customer_id = -1`).

## Remediation Steps
- Enable Adaptive Query Execution: `spark.sql.adaptive.enabled=true` and `spark.sql.adaptive.skewJoin.enabled=true`.
- Broadcast small dimension tables under 100 MB using `F.broadcast(dim_df)`.
- Apply key salting (`concat(key, '_', floor(rand() * 16))`) on skewed fact-to-fact joins.

Contact on-call lead at oncall-de@company.com or +1-415-555-0199 for P1 escalations.
