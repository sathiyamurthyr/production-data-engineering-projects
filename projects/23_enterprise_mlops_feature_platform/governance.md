# MLOps Governance Framework

## Overview

The MLOps governance framework ensures responsible AI development, deployment, and monitoring. It covers model approval workflows, audit logging, bias detection, explainability, and compliance.

## Governance Principles

### 1. Model Lifecycle Governance

Every model follows a governed lifecycle:

```
Development → Staging → Production → Archived
     ↓           ↓          ↓           ↓
  Training    Validation  A/B Test    Decommission
```

### 2. Approval Workflows

#### Model Approval Process

```python
class ModelApprovalWorkflow:
    """Model approval workflow."""
    
    STAGES = [
        "submission",
        "automated_validation",
        "technical_review",
        "security_review",
        "compliance_review",
        "deployment",
        "monitoring",
    ]
    
    def __init__(self):
        self.approvals = {}
    
    def submit_for_approval(self, model_version: ModelVersion) -> str:
        """Submit model for approval.
        
        Returns:
            Approval request ID
        """
        request_id = generate_request_id()
        self.approvals[request_id] = {
            "model_version": model_version,
            "stage": "submission",
            "approvals": {},
            "status": "pending",
        }
        return request_id
    
    def approve(self, request_id: str, approver: str, comments: str) -> bool:
        """Approve model at current stage.
        
        Args:
            request_id: Approval request ID
            approver: Approver name
            comments: Approval comments
            
        Returns:
            True if successful
        """
        if request_id not in self.approvals:
            return False
        
        approval = self.approvals[request_id]
        current_stage = approval["stage"]
        
        # Record approval
        approval["approvals"][current_stage] = {
            "approver": approver,
            "timestamp": datetime.now(),
            "comments": comments,
        }
        
        # Move to next stage
        next_stage = self._get_next_stage(current_stage)
        if next_stage:
            approval["stage"] = next_stage
        else:
            approval["status"] = "approved"
        
        return True
    
    def reject(self, request_id: str, rejector: str, reason: str) -> bool:
        """Reject model approval.
        
        Args:
            request_id: Approval request ID
            rejector: Person rejecting
            reason: Rejection reason
            
        Returns:
            True if successful
        """
        if request_id not in self.approvals:
            return False
        
        self.approvals[request_id]["status"] = "rejected"
        self.approvals[request_id]["rejection"] = {
            "rejector": rejector,
            "timestamp": datetime.now(),
            "reason": reason,
        }
        
        return True
```

### 3. Audit Logging

All model activities are logged for compliance:

```python
class AuditLogger:
    """Audit logging for model lifecycle."""
    
    def __init__(self, database_uri: str):
        """Initialize audit logger.
        
        Args:
            database_uri: Database connection URI
        """
        self.database_uri = database_uri
    
    def log_event(self, event: dict[str, Any]) -> None:
        """Log audit event.
        
        Args:
            event: Event details
        """
        audit_record = {
            "timestamp": datetime.now(),
            "event_type": event.get("type"),
            "actor": event.get("actor"),
            "model_name": event.get("model_name"),
            "model_version": event.get("model_version"),
            "details": event.get("details", {}),
            "ip_address": event.get("ip_address"),
            "user_agent": event.get("user_agent"),
        }
        
        # Store in database
        self._store_audit_record(audit_record)
    
    def log_model_training(self, model_name: str, run_id: str, user: str) -> None:
        """Log model training event."""
        self.log_event({
            "type": "model_training",
            "actor": user,
            "model_name": model_name,
            "details": {"run_id": run_id},
        })
    
    def log_model_deployment(self, model_name: str, version: str, user: str) -> None:
        """Log model deployment event."""
        self.log_event({
            "type": "model_deployment",
            "actor": user,
            "model_name": model_name,
            "model_version": version,
        })
    
    def log_model_prediction(self, model_name: str, version: str, user: str, input_data: dict) -> None:
        """Log model prediction event."""
        self.log_event({
            "type": "model_prediction",
            "actor": user,
            "model_name": model_name,
            "model_version": version,
            "details": {"input_features": list(input_data.keys())},
        })
```

### 4. Responsible AI

#### Bias Detection

```python
class BiasDetector:
    """Detect model bias across protected attributes."""
    
    def __init__(self):
        """Initialize bias detector."""
        pass
    
    def detect_bias(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        protected_attributes: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """Detect bias across protected attributes.
        
        Args:
            y_true: True labels
            y_pred: Predictions
            protected_attributes: Dictionary of protected attributes
            
        Returns:
            Bias metrics
        """
        from sklearn.metrics import confusion_matrix
        
        bias_results = {}
        
        for attribute_name, attribute_values in protected_attributes.items():
            # Get unique groups
            groups = np.unique(attribute_values)
            
            group_metrics = {}
            for group in groups:
                # Filter data for this group
                mask = attribute_values == group
                y_true_group = y_true[mask]
                y_pred_group = y_pred[mask]
                
                # Calculate metrics
                tn, fp, fn, tp = confusion_matrix(y_true_group, y_pred_group).ravel()
                
                group_metrics[str(group)] = {
                    "true_positive_rate": tp / (tp + fn) if (tp + fn) > 0 else 0,
                    "false_positive_rate": fp / (fp + tn) if (fp + tn) > 0 else 0,
                    "selection_rate": (tp + fp) / len(y_pred_group),
                    "count": len(y_pred_group),
                }
            
            # Calculate disparity
            selection_rates = [m["selection_rate"] for m in group_metrics.values()]
            max_rate = max(selection_rates)
            min_rate = min(selection_rates)
            
            bias_results[attribute_name] = {
                "groups": group_metrics,
                "disparity": max_rate / min_rate if min_rate > 0 else float('inf'),
                "is_biased": (max_rate / min_rate) > 1.5 if min_rate > 0 else True,
            }
        
        return bias_results
```

#### Explainability

```python
class ModelExplainer:
    """Model explainability using SHAP and LIME."""
    
    def __init__(self, model: Any, feature_names: list[str]):
        """Initialize model explainer.
        
        Args:
            model: Trained model
            feature_names: Feature names
        """
        self.model = model
        self.feature_names = feature_names
    
    def explain_prediction(self, X: np.ndarray) -> dict[str, Any]:
        """Explain individual predictions.
        
        Args:
            X: Input features
            
        Returns:
            Explanation
        """
        try:
            import shap
            
            # Create explainer
            explainer = shap.TreeExplainer(self.model)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(X)
            
            return {
                "feature_importance": dict(zip(self.feature_names, np.abs(shap_values).mean(axis=0))),
                "shap_values": shap_values.tolist(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def explain_global(self, X: np.ndarray) -> dict[str, Any]:
        """Explain model globally.
        
        Args:
            X: Input features
            
        Returns:
            Global explanation
        """
        try:
            import shap
            
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X)
            
            return {
                "feature_importance": dict(zip(self.feature_names, np.abs(shap_values).mean(axis=0))),
                "mean_shap_values": dict(zip(self.feature_names, shap_values.mean(axis=0))),
            }
        except Exception as e:
            return {"error": str(e)}
```

### 5. Model Cards

```python
class ModelCard:
    """Model card for documentation."""
    
    def __init__(self, model_name: str, model_version: str):
        """Initialize model card.
        
        Args:
            model_name: Model name
            model_version: Model version
        """
        self.model_name = model_name
        self.model_version = model_version
        self.content = {}
    
    def add_section(self, section: str, content: dict[str, Any]) -> None:
        """Add section to model card.
        
        Args:
            section: Section name
            content: Section content
        """
        self.content[section] = content
    
    def generate(self) -> dict[str, Any]:
        """Generate model card.
        
        Returns:
            Model card content
        """
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "generated_at": datetime.now().isoformat(),
            "sections": self.content,
        }
```

## Compliance

### Regulatory Compliance

#### GDPR
- Right to explanation
- Data minimization
- Audit trail

#### HIPAA (Healthcare)
- PHI protection
- Access controls
- Audit logging

#### PCI DSS (Payments)
- Fraud model transparency
- Data security
- Regular testing

## Security

### Model Access Control

```python
class ModelAccessControl:
    """Control access to models."""
    
    def __init__(self):
        """Initialize access control."""
        self.acl = {}
    
    def grant_access(self, model_name: str, user: str, permission: str) -> None:
        """Grant access to model.
        
        Args:
            model_name: Model name
            user: User/role
            permission: Permission (read, write, deploy)
        """
        if model_name not in self.acl:
            self.acl[model_name] = {}
        
        if user not in self.acl[model_name]:
            self.acl[model_name][user] = []
        
        self.acl[model_name][user].append(permission)
    
    def check_access(self, model_name: str, user: str, permission: str) -> bool:
        """Check if user has permission.
        
        Args:
            model_name: Model name
            user: User/role
            permission: Permission
            
        Returns:
            True if access granted
        """
        if model_name not in self.acl:
            return False
        
        if user not in self.acl[model_name]:
            return False
        
        return permission in self.acl[model_name][user]
```

## Monitoring

### Model Health Dashboard

Track:
- Model performance metrics
- Drift detection results
- Prediction volumes
- Latency metrics
- Error rates
- Business impact

## Best Practices

1. **Version Everything**: Models, data, code, configs
2. **Automate Testing**: Unit, integration, validation tests
3. **Monitor Continuously**: Drift, performance, business metrics
4. **Document Everything**: Model cards, runbooks, SOPs
5. **Audit All Actions**: Training, deployment, predictions
6. **Test in Staging**: A/B testing before production
7. **Rollback Ready**: Quick rollback procedures
8. **Train Team**: MLOps best practices

## Incident Response

### Model Failure Response

1. **Detection**: Monitoring alerts
2. **Assessment**: Impact analysis
3. **Response**: Rollback or fix
4. **Communication**: Stakeholder notification
5. **Post-mortem**: Root cause analysis
6. **Prevention**: Process improvements