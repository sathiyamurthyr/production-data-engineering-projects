"""Feature Definitions - Define and manage feature views."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lag, lead, window, avg, stddev, max, min


class FeatureType(str, Enum):
    """Types of features."""
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    VECTOR = "vector"


@dataclass
class FeatureDefinition:
    """Definition of a feature."""
    name: str
    feature_type: FeatureType
    description: str
    entity_id: str  # Primary key (e.g., customer_id, transaction_id)
    timestamp_col: str  # Event timestamp for point-in-time correctness
    
    # Feature computation
    source_table: str
    transformation: str  # SQL or PySpark transformation
    
    # Metadata
    owner: str
    domain: str
    tags: list[str] = field(default_factory=list)
    sensitivity: str = "internal"
    
    # Quality
    validation_rules: list[dict[str, Any]] = field(default_factory=list)
    monitoring_enabled: bool = True
    
    # Lineage
    upstream_features: list[str] = field(default_factory=list)
    upstream_sources: list[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class FeatureView:
    """Collection of features for a specific entity."""
    
    def __init__(
        self,
        name: str,
        entity_id: str,
        description: str,
        features: list[FeatureDefinition],
        ttl_days: int = 365,
    ):
        """Initialize feature view."""
        self.name = name
        self.entity_id = entity_id
        self.description = description
        self.features = features
        self.ttl_days = ttl_days
        self.created_at = datetime.now()
    
    def get_feature_names(self) -> list[str]:
        """Get all feature names."""
        return [f.name for f in self.features]
    
    def get_feature(self, name: str) -> FeatureDefinition | None:
        """Get feature by name."""
        for feature in self.features:
            if feature.name == name:
                return feature
        return None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "entity_id": self.entity_id,
            "description": self.description,
            "features": [
                {
                    "name": f.name,
                    "type": f.feature_type.value,
                    "description": f.description,
                    "source": f.source_table,
                    "transformation": f.transformation,
                }
                for f in self.features
            ],
            "ttl_days": self.ttl_days,
        }


class CustomerFeatures:
    """Customer feature definitions."""
    
    @staticmethod
    def create_feature_view() -> FeatureView:
        """Create customer feature view."""
        features = [
            # Demographics
            FeatureDefinition(
                name="customer_age",
                feature_type=FeatureType.NUMERICAL,
                description="Customer age in years",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.customers",
                transformation="age(current_date(), birth_date)",
                owner="data-science",
                domain="customer",
                tags=["demographic", "static"],
                validation_rules=[
                    {"rule": "range", "min": 18, "max": 120},
                ],
            ),
            FeatureDefinition(
                name="customer_tenure_months",
                feature_type=FeatureType.NUMERICAL,
                description="Months since customer registration",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.customers",
                transformation="months_between(current_date(), registration_date)",
                owner="data-science",
                domain="customer",
                tags=["demographic", "static"],
                validation_rules=[
                    {"rule": "range", "min": 0, "max": 600},
                ],
            ),
            
            # Transaction features
            FeatureDefinition(
                name="transaction_count_7d",
                feature_type=FeatureType.NUMERICAL,
                description="Number of transactions in last 7 days",
                entity_id="customer_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    COUNT(*) OVER (
                        PARTITION BY customer_id 
                        ORDER BY transaction_timestamp 
                        RANGE BETWEEN 7 DAYS PRECEDING AND CURRENT ROW
                    )
                """,
                owner="data-science",
                domain="transaction",
                tags=["transactional", "temporal"],
                upstream_sources=["silver.transactions"],
            ),
            FeatureDefinition(
                name="transaction_amount_avg_30d",
                feature_type=FeatureType.NUMERICAL,
                description="Average transaction amount in last 30 days",
                entity_id="customer_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    AVG(amount) OVER (
                        PARTITION BY customer_id 
                        ORDER BY transaction_timestamp 
                        RANGE BETWEEN 30 DAYS PRECEDING AND CURRENT ROW
                    )
                """,
                owner="data-science",
                domain="transaction",
                tags=["transactional", "temporal", "financial"],
                upstream_sources=["silver.transactions"],
            ),
            FeatureDefinition(
                name="transaction_amount_stddev_30d",
                feature_type=FeatureType.NUMERICAL,
                description="Standard deviation of transaction amounts in last 30 days",
                entity_id="customer_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    STDDEV(amount) OVER (
                        PARTITION BY customer_id 
                        ORDER BY transaction_timestamp 
                        RANGE BETWEEN 30 DAYS PRECEDING AND CURRENT ROW
                    )
                """,
                owner="data-science",
                domain="transaction",
                tags=["transactional", "temporal"],
                upstream_sources=["silver.transactions"],
            ),
            
            # Behavioral features
            FeatureDefinition(
                name="login_frequency_7d",
                feature_type=FeatureType.NUMERICAL,
                description="Number of logins in last 7 days",
                entity_id="customer_id",
                timestamp_col="login_timestamp",
                source_table="silver.user_activity",
                transformation="""
                    COUNT(*) OVER (
                        PARTITION BY customer_id 
                        ORDER BY login_timestamp 
                        RANGE BETWEEN 7 DAYS PRECEDING AND CURRENT ROW
                    )
                """,
                owner="data-science",
                domain="behavior",
                tags=["behavioral", "temporal"],
                upstream_sources=["silver.user_activity"],
            ),
            FeatureDefinition(
                name="days_since_last_activity",
                feature_type=FeatureType.NUMERICAL,
                description="Days since last customer activity",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.user_activity",
                transformation="days_between(current_date(), last_activity_date)",
                owner="data-science",
                domain="behavior",
                tags=["behavioral", "temporal"],
                upstream_sources=["silver.user_activity"],
            ),
            
            # Derived features
            FeatureDefinition(
                name="transaction_velocity_score",
                feature_type=FeatureType.NUMERICAL,
                description="Normalized transaction velocity score (0-1)",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="gold.customer_features",
                transformation="""
                    CASE 
                        WHEN transaction_count_7d > 10 THEN 1.0
                        WHEN transaction_count_7d > 5 THEN 0.7
                        WHEN transaction_count_7d > 2 THEN 0.4
                        ELSE 0.2
                    END
                """,
                owner="data-science",
                domain="derived",
                tags=["derived", "scored"],
                upstream_features=["transaction_count_7d"],
            ),
        ]
        
        return FeatureView(
            name="customer_features",
            entity_id="customer_id",
            description="Comprehensive customer feature set for ML models",
            features=features,
            ttl_days=365,
        )


class FraudDetectionFeatures:
    """Fraud detection feature definitions."""
    
    @staticmethod
    def create_feature_view() -> FeatureView:
        """Create fraud detection feature view."""
        features = [
            # Transaction features
            FeatureDefinition(
                name="transaction_amount",
                feature_type=FeatureType.NUMERICAL,
                description="Transaction amount in USD",
                entity_id="transaction_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="amount",
                owner="fraud-team",
                domain="fraud",
                tags=["transactional", "financial"],
            ),
            FeatureDefinition(
                name="transaction_amount_deviation",
                feature_type=FeatureType.NUMERICAL,
                description="Deviation from customer's average transaction amount",
                entity_id="transaction_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    (amount - avg_amount_30d) / nullif(stddev_amount_30d, 0)
                """,
                owner="fraud-team",
                domain="fraud",
                tags=["transactional", "statistical"],
                upstream_features=["transaction_amount_avg_30d"],
            ),
            
            # Velocity features
            FeatureDefinition(
                name="transaction_count_1h",
                feature_type=FeatureType.NUMERICAL,
                description="Number of transactions in last 1 hour",
                entity_id="customer_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    COUNT(*) OVER (
                        PARTITION BY customer_id 
                        ORDER BY transaction_timestamp 
                        RANGE BETWEEN 1 HOUR PRECEDING AND CURRENT ROW
                    )
                """,
                owner="fraud-team",
                domain="fraud",
                tags=["velocity", "temporal"],
                upstream_sources=["silver.transactions"],
            ),
            FeatureDefinition(
                name="transaction_count_24h",
                feature_type=FeatureType.NUMERICAL,
                description="Number of transactions in last 24 hours",
                entity_id="customer_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    COUNT(*) OVER (
                        PARTITION BY customer_id 
                        ORDER BY transaction_timestamp 
                        RANGE BETWEEN 24 HOURS PRECEDING AND CURRENT ROW
                    )
                """,
                owner="fraud-team",
                domain="fraud",
                tags=["velocity", "temporal"],
                upstream_sources=["silver.transactions"],
            ),
            
            # Geographic features
            FeatureDefinition(
                name="distance_from_home",
                feature_type=FeatureType.NUMERICAL,
                description="Distance from customer's home location (km)",
                entity_id="transaction_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    haversine_distance(
                        home_latitude, home_longitude,
                        merchant_latitude, merchant_longitude
                    )
                """,
                owner="fraud-team",
                domain="fraud",
                tags=["geographic", "behavioral"],
            ),
            FeatureDefinition(
                name="unusual_location_flag",
                feature_type=FeatureType.BOOLEAN,
                description="Flag if transaction is from unusual location",
                entity_id="transaction_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    CASE 
                        WHEN distance_from_home > 100 THEN true 
                        ELSE false 
                    END
                """,
                owner="fraud-team",
                domain="fraud",
                tags=["geographic", "anomaly"],
            ),
            
            # Device features
            FeatureDefinition(
                name="device_change_flag",
                feature_type=FeatureType.BOOLEAN,
                description="Flag if customer used new device",
                entity_id="transaction_id",
                timestamp_col="transaction_timestamp",
                source_table="silver.transactions",
                transformation="""
                    CASE 
                        WHEN device_id != last_known_device_id THEN true 
                        ELSE false 
                    END
                """,
                owner="fraud-team",
                domain="fraud",
                tags=["device", "anomaly"],
            ),
        ]
        
        return FeatureView(
            name="fraud_detection_features",
            entity_id="transaction_id",
            description="Feature set for fraud detection model",
            features=features,
            ttl_days=90,
        )


class CreditRiskFeatures:
    """Credit risk feature definitions."""
    
    @staticmethod
    def create_feature_view() -> FeatureView:
        """Create credit risk feature view."""
        features = [
            # Credit history
            FeatureDefinition(
                name="credit_score",
                feature_type=FeatureType.NUMERICAL,
                description="FICO credit score",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.credit_bureau",
                transformation="fico_score",
                owner="risk-team",
                domain="credit",
                tags=["credit", "bureau"],
                validation_rules=[
                    {"rule": "range", "min": 300, "max": 850},
                ],
            ),
            FeatureDefinition(
                name="debt_to_income_ratio",
                feature_type=FeatureType.NUMERICAL,
                description="Debt to income ratio",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.financial",
                transformation="total_debt / annual_income",
                owner="risk-team",
                domain="credit",
                tags=["financial", "credit"],
                validation_rules=[
                    {"rule": "range", "min": 0, "max": 2},
                ],
            ),
            FeatureDefinition(
                name="payment_history_months",
                feature_type=FeatureType.NUMERICAL,
                description="Months of payment history",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.credit_bureau",
                transformation="months_since_first_account",
                owner="risk-team",
                domain="credit",
                tags=["credit", "history"],
            ),
            
            # Behavioral features
            FeatureDefinition(
                name="late_payment_count_12m",
                feature_type=FeatureType.NUMERICAL,
                description="Number of late payments in last 12 months",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.payment_history",
                transformation="""
                    COUNT(CASE WHEN payment_status = 'late' THEN 1 END)
                """,
                owner="risk-team",
                domain="credit",
                tags=["payment", "behavioral"],
                upstream_sources=["silver.payment_history"],
            ),
            FeatureDefinition(
                name="credit_utilization_ratio",
                feature_type=FeatureType.NUMERICAL,
                description="Credit utilization ratio",
                entity_id="customer_id",
                timestamp_col="event_timestamp",
                source_table="silver.credit_bureau",
                transformation="total_balance / total_credit_limit",
                owner="risk-team",
                domain="credit",
                tags=["credit", "utilization"],
                validation_rules=[
                    {"rule": "range", "min": 0, "max": 1},
                ],
            ),
        ]
        
        return FeatureView(
            name="credit_risk_features",
            entity_id="customer_id",
            description="Feature set for credit risk scoring model",
            features=features,
            ttl_days=180,
        )