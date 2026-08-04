# Enterprise MLOps & Feature Platform - Interview Questions

## Table of Contents

1. [MLOps Fundamentals](#mlops-fundamentals)
2. [Feature Engineering](#feature-engineering)
3. [Feature Store](#feature-store)
4. [Model Registry](#model-registry)
5. [Experiment Tracking](#experiment-tracking)
6. [ML Pipelines](#ml-pipelines)
7. [Model Serving](#model-serving)
8. [Monitoring & Drift Detection](#monitoring--drift-detection)
9. [AI Governance](#ai-governance)
10. [Production Operations](#production-operations)

---

## MLOps Fundamentals

### 1. What is MLOps and how does it differ from traditional DevOps?

**Answer:**
MLOps applies DevOps principles to machine learning systems. Key differences:

| Aspect | DevOps | MLOps |
|--------|--------|-------|
| **Artifacts** | Code, binaries | Models, data, code, configs |
| **Testing** | Unit tests, integration tests | Model validation, data validation, drift detection |
| **Deployment** | Continuous deployment | Model promotion, A/B testing, canary |
| **Monitoring** | Application metrics | Model performance, data drift, concept drift |
| **Versioning** | Code versioning | Model versioning, data versioning, experiment tracking |

### 2. What are the core components of an MLOps platform?

**Answer:**
1. **Feature Store**: Offline/online feature management
2. **Experiment Tracking**: MLflow, Weights & Biases
3. **Model Registry**: Versioned model storage
4. **Training Pipelines**: Automated training workflows
5. **Model Serving**: REST/gRPC endpoints
6. **Monitoring**: Drift detection, performance tracking
7. **Governance**: Approval workflows, audit logging

### 3. Explain the ML lifecycle in production.

**Answer:**
```
Data Collection → Feature Engineering → Model Training → Validation
                                                    ↓
                                    Staging ← Registry ← Experiment Tracking
                                    ↓
                              A/B Testing
                                    ↓
                              Production
                                    ↓
                              Monitoring → Drift Detection → Retraining
```

### 4. What is the difference between batch and online inference?

**Answer:**

**Batch Inference:**
- Scheduled predictions on large datasets
- Higher latency tolerance (minutes to hours)
- Cost-effective for bulk predictions
- Examples: Daily fraud scores, weekly recommendations

**Online (Real-time) Inference:**
- Immediate predictions on single requests
- Low latency requirement (< 100ms)
- Higher infrastructure cost
- Examples: Real-time fraud detection, recommendation API

### 5. What is feature engineering and why is it important?

**Answer:**
Feature engineering transforms raw data into features for ML models:

- **Importance**: Directly impacts model performance
- **Challenges**: Time-consuming, requires domain expertise
- **Best Practices**: Reusable features, feature stores, automated feature engineering
- **Production Considerations**: Feature consistency, monitoring, versioning

---

## Feature Engineering

### 6. What is a feature store and why do you need one?

**Answer:**
A feature store is a centralized repository for features:

- **Reusability**: Share features across models and teams
- **Consistency**: Same features for training and inference
- **Performance**: Offline store for training, online store for serving
- **Lineage**: Track feature dependencies and transformations
- **Quality**: Validation, monitoring, and alerting

### 7. Explain offline vs online feature stores.

**Answer:**

**Offline Feature Store:**
- Storage: Data Lake (Delta Lake, S3, ADLS)
- Purpose: Training, batch inference
- Latency: Minutes to hours
- Data: Historical, point-in-time correct

**Online Feature Store:**
- Storage: Redis, Cassandra, DynamoDB
- Purpose: Real-time inference
- Latency: < 10ms
- Data: Latest values, low-latency access

### 8. What is point-in-time correctness?

**Answer:**
Point-in-time correctness ensures features are computed using only data available at the prediction time, preventing data leakage:

```python
# WRONG: Uses future data
features = df.filter(col("transaction_date") <= prediction_date)

# CORRECT: Uses only data available at prediction time
features = df.filter(col("transaction_timestamp") <= prediction_timestamp)
```

### 9. How do you handle feature drift?

**Answer:**
1. **Monitor**: Track feature statistics over time
2. **Detect**: Statistical tests (KS test, PSI)
3. **Alert**: Notify when drift exceeds threshold
4. **Remediate**: Retrain model, update features
5. **Prevent**: Feature engineering best practices

### 10. What is feature versioning?

**Answer:**
Feature versioning tracks changes to features over time:
- Schema versioning (column additions, type changes)
- Transformation versioning (code changes)
- Point-in-time replay (recompute features as of specific date)
- Rollback capability (revert to previous feature version)

---

## Feature Store

### 11. Describe the architecture of a feature store.

**Answer:**
```
┌─────────────────────────────────────────┐
│         Feature Registry                 │
│  (Metadata, Lineage, Discovery)          │
├─────────────────────────────────────────┤
│         Feature Serving Layer            │
│  (REST API, SDK, Online Store)           │
├─────────────────────────────────────────┤
│         Feature Computation Layer         │
│  (Batch, Streaming, Transformation)       │
├─────────────────────────────────────────┤
│         Storage Layer                     │
│  (Offline: Delta Lake, Online: Redis)     │
└─────────────────────────────────────────┘
```

### 12. How do you ensure feature consistency between training and serving?

**Answer:**
1. **Shared Code**: Same transformation logic for both
2. **Point-in-Time**: Use event timestamps, not processing timestamps
3. **Feature Versioning**: Tag features used in training
4. **Materialization**: Pre-compute features for serving
5. **Validation**: Compare training/serving feature distributions

### 13. What is feature materialization?

**Answer:**
Feature materialization pre-computes and stores features for fast serving:

```python
# Batch materialization (daily)
features_df = compute_features(as_of_date=datetime.now())
features_df.write.format("delta").mode("overwrite").saveAsTable("gold.features")

# Streaming materialization (real-time)
streaming_df = spark.readStream.table("silver.events")
features_df = compute_features_streaming(streaming_df)
features_df.writeStream.format("delta").outputMode("append").start()
```

### 14. How do you handle feature dependencies?

**Answer:**
- **Lineage Tracking**: Graph of feature dependencies
- **Topological Sort**: Compute features in dependency order
- **Incremental Updates**: Only recompute affected features
- **Validation**: Test feature quality after upstream changes
- **Documentation**: Auto-generated from code and metadata

---

## Model Registry

### 15. What is a model registry?

**Answer:**
A model registry stores, versions, and manages ML models:
- **Versioning**: Semantic versioning (MAJOR.MINOR.PATCH)
- **Stages**: Development → Staging → Production
- **Metadata**: Hyperparameters, metrics, training data
- **Artifacts**: Model files, requirements, documentation
- **Promotion**: Automated and manual promotion workflows

### 16. Explain model versioning strategies.

**Answer:**
- **Semantic Versioning**: MAJOR.MINOR.PATCH
  - MAJOR: Breaking changes
  - MINOR: New features, backward compatible
  - PATCH: Bug fixes
- **Timestamp-based**: v20240101_120000
- **Git SHA**: vabc1234
- **Incremental**: v1, v2, v3

### 17. What is model promotion workflow?

**Answer:**
```
Development → [Automated Tests] → Staging → [A/B Test] → Production
     ↓              ↓                   ↓           ↓            ↓
  Training      Validation          Staging     Compare      Monitor
```

### 18. How do you handle model rollback?

**Answer:**
1. **Archive Current**: Move current production model to Archived
2. **Promote Previous**: Promote target version to Production
3. **Update Serving**: Hot-swap model in serving endpoint
4. **Verify**: Health checks and smoke tests
5. **Monitor**: Track metrics after rollback

### 19. What metadata should you store with models?

**Answer:**
- **Training**: Dataset version, algorithm, hyperparameters
- **Metrics**: AUC, precision, recall, latency
- **Artifacts**: Model file, requirements.txt, conda.yaml
- **Environment**: Python version, OS, library versions
- **Lineage**: Feature store version, code commit SHA
- **Approval**: Who approved, when, comments

---

## Experiment Tracking

### 20. What is experiment tracking?

**Answer:**
Experiment tracking records all aspects of ML experiments:
- **Parameters**: Hyperparameters, config
- **Metrics**: Loss, accuracy, AUC over time
- **Artifacts**: Models, plots, logs
- **Code**: Git commit, code version
- **Environment**: Dependencies, hardware

### 21. How does MLflow work?

**Answer:**
MLflow provides:
- **Tracking**: Log experiments via API or SDK
- **Projects**: Package code with dependencies
- **Models**: Standardized model format
- **Registry**: Centralized model management

```python
import mlflow

# Start experiment
mlflow.set_experiment("fraud_detection")
with mlflow.start_run():
    # Log parameters
    mlflow.log_params({"max_depth": 6, "learning_rate": 0.1})
    
    # Log metrics
    mlflow.log_metrics({"auc": 0.95, "precision": 0.92})
    
    # Log model
    mlflow.sklearn.log_model(model, "model")
```

### 22. What are hyperparameters and how do you tune them?

**Answer:**
Hyperparameters are model configuration settings:
- **Examples**: Learning rate, max_depth, n_estimators
- **Tuning Methods**:
  - Grid Search: Exhaustive search
  - Random Search: Random sampling
  - Bayesian Optimization: Smart search (Optuna, Hyperopt)

```python
import optuna

def objective(trial):
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
    }
    model = train_model(params)
    return model.score(X_val, y_val)

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=100)
```

### 23. How do you compare experiments?

**Answer:**
- **Metrics Comparison**: Side-by-side metric comparison
- **Hyperparameter Analysis**: Identify best configurations
- **Statistical Significance**: Ensure improvements are real
- **Visualization**: Parallel coordinates, scatter plots
- **Artifacts**: Compare model outputs, confusion matrices

---

## ML Pipelines

### 24. What is an ML pipeline?

**Answer:**
An ML pipeline automates the ML workflow:
1. **Data Extraction**: Pull features from feature store
2. **Data Validation**: Great Expectations suite
3. **Model Training**: Train with current data
4. **Model Validation**: Evaluate performance
5. **Model Registration**: Register in MLflow
6. **Deployment**: Promote to staging/production

### 25. How do you orchestrate ML pipelines?

**Answer:**
- **Airflow**: DAG-based orchestration
- **Prefect**: Modern Python-native orchestration
- **Kubeflow Pipelines**: Kubernetes-native
- **Databricks Workflows**: For Databricks users
- **GitHub Actions**: CI/CD for ML

### 26. What is continuous training?

**Answer:**
Continuous training automatically retrains models when:
- New data is available
- Model performance degrades
- Scheduled time (weekly, monthly)
- Manual trigger

```python
# Airflow DAG
with DAG("training_pipeline", schedule_interval="@daily") as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_features)
    train = PythonOperator(task_id="train", python_callable=train_model)
    validate = PythonOperator(task_id="validate", python_callable=validate_model)
    deploy = PythonOperator(task_id="deploy", python_callable=deploy_model)
    
    extract >> train >> validate >> deploy
```

### 27. How do you handle pipeline failures?

**Answer:**
1. **Retry Logic**: Automatic retries with backoff
2. **Alerting**: Notify on failure
3. **Checkpointing**: Resume from failure point
4. **Fallback**: Use previous model if new model fails
5. **Rollback**: Revert to previous pipeline version

---

## Model Serving

### 28. What are the different model serving patterns?

**Answer:**

**REST API (Online)**
- FastAPI, Flask, TorchServe
- Low latency (< 100ms)
- Single predictions

**Batch Inference**
- Spark, Airflow
- High throughput
- Scheduled predictions

**Streaming Inference**
- Kafka, Spark Structured Streaming
- Real-time predictions
- Continuous data flow

### 29. How do you implement A/B testing for models?

**Answer:**
```python
class ABTestRouter:
    def route(self, user_id):
        # Deterministic hash for consistent routing
        hash_val = hash(f"{user_id}:{experiment_id}")
        variant = hash_val % 100
        
        if variant < traffic_split:
            return challenger_model
        else:
            return champion_model
```

### 30. What is champion/challenger deployment?

**Answer:**
- **Champion**: Current production model
- **Challenger**: New model being tested
- **Traffic Split**: Percentage routed to challenger
- **Comparison**: Track metrics for both
- **Promotion**: Challenger becomes champion if better

### 31. How do you handle model versioning in serving?

**Answer:**
- **Version Aliases**: Latest, staging, production
- **Hot Swapping**: Load new model without downtime
- **Canary Deployment**: Gradual rollout
- **Rollback**: Quick revert to previous version
- **Model Caching**: Keep multiple models in memory

---

## Monitoring & Drift Detection

### 32. What types of drift do you monitor?

**Answer:**

**Data Drift**: Input feature distribution changes
- Statistical tests: KS test, PSI, chi-squared
- Threshold: p-value < 0.05

**Concept Drift**: Relationship between features and target changes
- Model performance degradation
- Business metric changes

**Prediction Drift**: Model output distribution changes
- Prediction distribution monitoring
- Confidence score tracking

### 33. How do you detect data drift?

**Answer:**
```python
# Kolmogorov-Smirnov test
from scipy import stats
ks_statistic, p_value = stats.ks_2samp(reference_data, current_data)

# Population Stability Index (PSI)
psi = calculate_psi(reference_data, current_data)

# Drift detected if
is_drifted = p_value < 0.05 or psi > 0.2
```

### 34. What metrics do you monitor for models?

**Answer:**

**Performance Metrics**
- Accuracy, precision, recall, F1
- AUC-ROC, AUC-PR
- Latency (p50, p95, p99)
- Throughput (predictions/second)

**Business Metrics**
- False positive rate
- Revenue impact
- Customer satisfaction

**Operational Metrics**
- Error rate
- Feature freshness
- Model staleness

### 35. How do you set up alerts for model monitoring?

**Answer:**
```python
# Alert conditions
alerts = {
    "drift_detected": drift_score > threshold,
    "performance_drop": accuracy_drop > 0.05,
    "high_latency": p99_latency > 1000,  # ms
    "error_rate_spike": error_rate > 0.01,
    "low_prediction_volume": predictions_per_hour < 1000,
}

# Notification channels
for alert_type, is_triggered in alerts.items():
    if is_triggered:
        send_alert(alert_type, severity="high")
```

---

## AI Governance

### 36. What is AI governance?

**Answer:**
AI governance ensures responsible AI development:
- **Model Approval**: Multi-stage approval workflow
- **Audit Logging**: Track all model activities
- **Bias Detection**: Fairness metrics across protected attributes
- **Explainability**: SHAP, LIME for model interpretability
- **Compliance**: GDPR, HIPAA, PCI DSS

### 37. How do you detect model bias?

**Answer:**
```python
from sklearn.metrics import confusion_matrix

def detect_bias(y_true, y_pred, protected_attr):
    groups = np.unique(protected_attr)
    
    for group in groups:
        mask = protected_attr == group
        tn, fp, fn, tp = confusion_matrix(y_true[mask], y_pred[mask]).ravel()
        
        tpr = tp / (tp + fn)  # True Positive Rate
        fpr = fp / (fp + tn)  # False Positive Rate
        
        print(f"Group {group}: TPR={tpr:.2f}, FPR={fpr:.2f}")
```

### 38. What is explainability and why is it important?

**Answer:**
Explainability makes model decisions interpretable:
- **SHAP**: Feature importance per prediction
- **LIME**: Local explanations
- **Feature Importance**: Global model behavior
- **Partial Dependence**: Feature impact on predictions
- **Importance**: Regulatory compliance, trust, debugging

### 39. What are model cards?

**Answer:**
Model cards document models for stakeholders:
- **Model Details**: Name, version, type
- **Intended Use**: Use cases, users, out-of-scope
- **Metrics**: Performance on various datasets
- **Limitations**: Known issues, biases
- **Ethical Considerations**: Fairness, privacy

### 40. How do you ensure regulatory compliance?

**Answer:**
- **GDPR**: Right to explanation, data minimization
- **HIPAA**: PHI protection, access controls
- **PCI DSS**: Fraud model transparency
- **Audit Trail**: Log all model decisions
- **Documentation**: Complete model documentation

---

## Production Operations

### 41. How do you handle model retraining?

**Answer:**
Triggers:
- **Performance Drop**: AUC drops below threshold
- **Data Drift**: Significant feature distribution changes
- **Scheduled**: Weekly, monthly retraining
- **New Data**: Sufficient new data collected
- **Manual**: Triggered by data scientist

Process:
1. Detect trigger
2. Extract new training data
3. Train model
4. Validate performance
5. A/B test
6. Promote if better

### 42. What is continuous delivery for ML?

**Answer:**
Continuous Delivery for ML (CD4ML) automates the entire ML pipeline:
- **Continuous Integration**: Test code and data
- **Continuous Training**: Automated retraining
- **Continuous Deployment**: Automated model deployment
- **Continuous Monitoring**: Track performance and drift

### 43. How do you manage training data?

**Answer:**
- **Versioning**: DVC, Delta Lake time travel
- **Lineage**: Track data sources and transformations
- **Quality**: Great Expectations validation
- **Labeling**: Consistent labeling guidelines
- **Privacy**: Anonymization, PII detection

### 44. What is the role of a feature platform team?

**Answer:**
- **Infrastructure**: Maintain feature store, serving
- **Standards**: Feature naming, documentation, quality
- **Support**: Help teams use features effectively
- **Governance**: Feature approval, access control
- **Optimization**: Performance, cost, scalability

### 45. How do you measure MLOps maturity?

**Answer:**
Levels:
1. **Level 0**: Manual, ad-hoc ML
2. **Level 1**: ML pipeline automation
3. **Level 2**: CI/CD for ML
4. **Level 3**: Full MLOps with monitoring and retraining
5. **Level 4**: Automated MLOps with full governance

Metrics:
- Deployment frequency
- Lead time for changes
- Model availability
- Time to detect drift
- Time to remediate

---

## Scenario-Based Questions

### 46. Your model's performance dropped by 10%. How do you investigate?

**Answer:**
1. **Check Data Drift**: Compare feature distributions
2. **Check Concept Drift**: Analyze model performance by segment
3. **Check Prediction Drift**: Monitor prediction distributions
4. **Check Data Quality**: Missing values, outliers
5. **Check Infrastructure**: Latency, errors
6. **Review Recent Changes**: Code, data, features
7. **Root Cause Analysis**: Identify underlying cause
8. **Remediation**: Retrain or rollback

### 47. How do you reduce model inference latency?

**Answer:**
- **Model Optimization**: Quantization, pruning, ONNX
- **Batching**: Batch predictions when possible
- **Caching**: Cache frequent predictions
- **Hardware**: GPU/TPU acceleration
- **Model Size**: Smaller models, knowledge distillation
- **Edge Deployment**: Deploy closer to users

### 48. Design a fraud detection system.

**Answer:**
1. **Features**: Transaction velocity, amount deviation, location
2. **Model**: Real-time XGBoost/LightGBM
3. **Serving**: Online inference < 10ms
4. **Monitoring**: Data drift, prediction drift
5. **Retraining**: Daily with new fraud patterns
6. **Explainability**: SHAP for each prediction
7. **Governance**: Model approval, audit logging

### 49. How do you handle imbalanced datasets?

**Answer:**
- **Sampling**: SMOTE, undersampling, oversampling
- **Class Weights**: Weighted loss function
- **Ensemble**: Balanced random forest
- **Metrics**: Use AUC-PR, F1, not accuracy
- **Threshold Tuning**: Adjust classification threshold
- **Anomaly Detection**: Treat as outlier detection

### 50. Explain the trade-offs between model complexity and interpretability.

**Answer:**
- **Simple Models** (Linear Regression, Decision Trees)
  - Pros: Interpretable, fast, stable
  - Cons: Lower accuracy, limited complexity

- **Complex Models** (Deep Learning, Ensembles)
  - Pros: High accuracy, handle complex patterns
  - Cons: Black box, requires explainability tools

- **Trade-off**: Start simple, increase complexity only when needed
- **Solution**: Use SHAP/LIME for complex models

---

## Quick Reference

### Key Terms
- **Feature Store**: Centralized feature repository
- **Model Registry**: Versioned model storage
- **Experiment Tracking**: MLflow, W&B
- **Drift Detection**: Data, concept, prediction drift
- **A/B Testing**: Champion vs challenger
- **Model Promotion**: Development → Staging → Production

### Essential Tools
- **MLflow**: Experiment tracking and model registry
- **Feature Stores: Feast, Tecton, Databricks Feature Store
- **Serving: FastAPI, TorchServe, Seldon Core
- **Monitoring: Evidently, Prometheus, Grafana
- **Orchestration: Airflow, Prefect, Kubeflow

### Common Patterns
- **Training Pipeline**: Extract → Train → Validate → Register
- **Inference Pipeline**: Request → Features → Model → Response
- **Retraining Pipeline: Monitor → Detect → Retrain → Validate → Deploy