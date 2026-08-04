"""
Cost Governance for Cross-Cloud Platform

This module provides cost management and chargeback across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field
from .identity_federation import CloudProvider

logger = logging.getLogger(__name__)


class CostCategory(str, Enum):
    """Cost categories"""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORKING = "networking"
    DATABASE = "database"
    AI_ML = "ai-ml"
    STREAMING = "streaming"
    MONITORING = "monitoring"
    SECURITY = "security"


class CostRecord(BaseModel):
    """Cost record"""
    record_id: str
    resource_id: str
    resource_type: str
    cloud: CloudProvider
    category: CostCategory
    cost: Decimal
    currency: str
    billing_period_start: datetime
    billing_period_end: datetime
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Budget(BaseModel):
    """Budget definition"""
    budget_id: str
    name: str
    description: str
    cloud: Optional[CloudProvider] = None  # None for cross-cloud
    category: Optional[CostCategory] = None
    amount: Decimal
    currency: str
    period: str  # monthly, quarterly, yearly
    alert_thresholds: List[float]  # [0.5, 0.8, 0.95]
    enabled: bool = True
    created_at: datetime
    updated_at: datetime


class CostGovernance:
    """
    Cross-cloud cost governance
    
    This service provides:
    - Cost tracking and allocation
    - Budget management
    - Chargeback and showback
    - Cost optimization recommendations
    """
    
    def __init__(self, config: Dict):
        """
        Initialize cost governance
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.cost_records: Dict[str, CostRecord] = {}
        self.budgets: Dict[str, Budget] = {}
        
        # Load default budgets
        self._load_default_budgets()
        
        logger.info("Cost Governance initialized")
    
    def _load_default_budgets(self) -> None:
        """Load default budgets"""
        default_budgets = [
            Budget(
                budget_id="platform-monthly-budget",
                name="Platform Monthly Budget",
                description="Overall platform monthly budget",
                amount=Decimal("50000"),
                currency="USD",
                period="monthly",
                alert_thresholds=[0.5, 0.8, 0.95],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Budget(
                budget_id="compute-budget",
                name="Compute Budget",
                description="Compute resources budget",
                category=CostCategory.COMPUTE,
                amount=Decimal("20000"),
                currency="USD",
                period="monthly",
                alert_thresholds=[0.7, 0.9],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Budget(
                budget_id="storage-budget",
                name="Storage Budget",
                description="Storage resources budget",
                category=CostCategory.STORAGE,
                amount=Decimal("10000"),
                currency="USD",
                period="monthly",
                alert_thresholds=[0.7, 0.9],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Budget(
                budget_id="azure-monthly-budget",
                name="Azure Monthly Budget",
                description="Azure cloud monthly budget",
                cloud=CloudProvider.AZURE,
                amount=Decimal("30000"),
                currency="USD",
                period="monthly",
                alert_thresholds=[0.5, 0.8, 0.95],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Budget(
                budget_id="aws-monthly-budget",
                name="AWS Monthly Budget",
                description="AWS cloud monthly budget",
                cloud=CloudProvider.AWS,
                amount=Decimal("20000"),
                currency="USD",
                period="monthly",
                alert_thresholds=[0.5, 0.8, 0.95],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        for budget in default_budgets:
            self.budgets[budget.budget_id] = budget
    
    async def record_cost(
        self,
        resource_id: str,
        resource_type: str,
        cloud: CloudProvider,
        category: CostCategory,
        cost: Decimal,
        currency: str,
        billing_period_start: datetime,
        billing_period_end: datetime,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostRecord:
        """
        Record cost for resource
        
        Args:
            resource_id: Resource ID
            resource_type: Resource type
            cloud: Cloud provider
            category: Cost category
            cost: Cost amount
            currency: Currency code
            billing_period_start: Billing period start
            billing_period_end: Billing period end
            tags: Resource tags
            metadata: Additional metadata
            
        Returns:
            Cost record
        """
        logger.info(f"Recording cost for resource {resource_id}")
        
        # Generate record ID
        record_id = f"cost-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{resource_id}"
        
        # Create cost record
        record = CostRecord(
            record_id=record_id,
            resource_id=resource_id,
            resource_type=resource_type,
            cloud=cloud,
            category=category,
            cost=cost,
            currency=currency,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        # Store record
        self.cost_records[record_id] = record
        
        # Check budgets
        await self._check_budgets(record)
        
        logger.info(f"Cost recorded: {record_id}")
        return record
    
    async def _check_budgets(self, record: CostRecord) -> None:
        """
        Check if cost exceeds budget thresholds
        
        Args:
            record: Cost record
        """
        # Get applicable budgets
        applicable_budgets = []
        for budget in self.budgets.values():
            if not budget.enabled:
                continue
            
            # Check cloud match
            if budget.cloud and budget.cloud != record.cloud:
                continue
            
            # Check category match
            if budget.category and budget.category != record.category:
                continue
            
            applicable_budgets.append(budget)
        
        # Check each budget
        for budget in applicable_budgets:
            await self._evaluate_budget(budget, record)
    
    async def _evaluate_budget(self, budget: Budget, record: CostRecord) -> None:
        """
        Evaluate budget for cost record
        
        Args:
            budget: Budget definition
            record: Cost record
        """
        # Calculate current spend for budget period
        current_spend = await self._calculate_budget_spend(budget)
        
        # Calculate percentage
        percentage = float(current_spend / budget.amount) if budget.amount > 0 else 0
        
        # Check thresholds
        for threshold in budget.alert_thresholds:
            if percentage >= threshold and percentage < threshold + 0.05:
                logger.warning(
                    f"Budget {budget.budget_id} at {percentage:.1%} "
                    f"(threshold: {threshold:.1%})"
                )
                
                # In real implementation, send alert
    
    async def _calculate_budget_spend(self, budget: Budget) -> Decimal:
        """
        Calculate current spend for budget
        
        Args:
            budget: Budget definition
            
        Returns:
            Current spend
        """
        # Determine period start and end
        period_end = datetime.utcnow()
        if budget.period == "monthly":
            period_start = period_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == "quarterly":
            quarter = (period_end.month - 1) // 3
            period_start = period_end.replace(month=quarter * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == "yearly":
            period_start = period_end.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            period_start = period_end - timedelta(days=30)
        
        # Sum costs
        total = Decimal("0")
        for record in self.cost_records.values():
            if record.billing_period_start >= period_start and record.billing_period_end <= period_end:
                # Check cloud match
                if budget.cloud and record.cloud != budget.cloud:
                    continue
                
                # Check category match
                if budget.category and record.category != budget.category:
                    continue
                
                total += record.cost
        
        return total
    
    async def create_budget(self, budget: Budget) -> Budget:
        """
        Create new budget
        
        Args:
            budget: Budget definition
            
        Returns:
            Created budget
        """
        logger.info(f"Creating budget: {budget.budget_id}")
        
        if budget.budget_id in self.budgets:
            raise ValueError(f"Budget already exists: {budget.budget_id}")
        
        self.budgets[budget.budget_id] = budget
        
        logger.info(f"Budget created: {budget.budget_id}")
        return budget
    
    async def get_budget(self, budget_id: str) -> Optional[Budget]:
        """
        Get budget by ID
        
        Args:
            budget_id: Budget ID
            
        Returns:
            Budget if found, None otherwise
        """
        return self.budgets.get(budget_id)
    
    async def get_cost_summary(
        self,
        cloud: Optional[CloudProvider] = None,
        category: Optional[CostCategory] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get cost summary
        
        Args:
            cloud: Cloud provider (optional)
            category: Cost category (optional)
            period_days: Period in days
            
        Returns:
            Cost summary
        """
        # Calculate period
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Filter records
        records = []
        for record in self.cost_records.values():
            if record.billing_period_start < period_start or record.billing_period_end > period_end:
                continue
            
            if cloud and record.cloud != cloud:
                continue
            
            if category and record.category != category:
                continue
            
            records.append(record)
        
        # Calculate totals
        total_cost = sum(record.cost for record in records)
        
        # Group by cloud
        by_cloud = {}
        for record in records:
            cloud_name = record.cloud.value
            if cloud_name not in by_cloud:
                by_cloud[cloud_name] = Decimal("0")
            by_cloud[cloud_name] += record.cost
        
        # Group by category
        by_category = {}
        for record in records:
            category_name = record.category.value
            if category_name not in by_category:
                by_category[category_name] = Decimal("0")
            by_category[category_name] += record.cost
        
        # Group by day
        by_day = {}
        for record in records:
            day_key = record.billing_period_start.strftime("%Y-%m-%d")
            if day_key not in by_day:
                by_day[day_key] = Decimal("0")
            by_day[day_key] += record.cost
        
        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_cost": str(total_cost),
            "by_cloud": {k: str(v) for k, v in by_cloud.items()},
            "by_category": {k: str(v) for k, v in by_category.items()},
            "by_day": {k: str(v) for k, v in by_day.items()},
            "record_count": len(records)
        }
    
    async def get_chargeback_report(
        self,
        period_days: int = 30,
        group_by: str = "team"
    ) -> Dict[str, Any]:
        """
        Get chargeback report
        
        Args:
            period_days: Period in days
            group_by: Grouping field (team, environment, project)
            
        Returns:
            Chargeback report
        """
        # Calculate period
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Group costs
        chargeback = {}
        
        for record in self.cost_records.values():
            if record.billing_period_start < period_start or record.billing_period_end > period_end:
                continue
            
            # Get group key
            if group_by == "team":
                key = record.tags.get("team", "unassigned")
            elif group_by == "environment":
                key = record.tags.get("environment", "unassigned")
            elif group_by == "project":
                key = record.tags.get("project", "unassigned")
            else:
                key = "unassigned"
            
            if key not in chargeback:
                chargeback[key] = {
                    "total_cost": Decimal("0"),
                    "by_cloud": {},
                    "by_category": {},
                    "resource_count": 0
                }
            
            chargeback[key]["total_cost"] += record.cost
            chargeback[key]["resource_count"] += 1
            
            # By cloud
            cloud_name = record.cloud.value
            if cloud_name not in chargeback[key]["by_cloud"]:
                chargeback[key]["by_cloud"][cloud_name] = Decimal("0")
            chargeback[key]["by_cloud"][cloud_name] += record.cost
            
            # By category
            category_name = record.category.value
            if category_name not in chargeback[key]["by_category"]:
                chargeback[key]["by_category"][category_name] = Decimal("0")
            chargeback[key]["by_category"][category_name] += record.cost
        
        # Convert to serializable format
        result = {}
        for key, value in chargeback.items():
            result[key] = {
                "total_cost": str(value["total_cost"]),
                "by_cloud": {k: str(v) for k, v in value["by_cloud"].items()},
                "by_category": {k: str(v) for k, v in value["by_category"].items()},
                "resource_count": value["resource_count"]
            }
        
        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "grouped_by": group_by,
            "chargeback": result
        }
    
    async def get_cost_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get cost optimization recommendations
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Analyze cost records
        for record in self.cost_records.values():
            # Check for underutilized resources
            if record.category == CostCategory.COMPUTE:
                cpu_utilization = record.metadata.get("cpu_utilization", 100)
                if cpu_utilization < 30:
                    recommendations.append({
                        "type": "downsize",
                        "resource_id": record.resource_id,
                        "cloud": record.cloud.value,
                        "category": record.category.value,
                        "current_cost": str(record.cost),
                        "potential_savings": str(record.cost * Decimal("0.5")),
                        "recommendation": f"Resource {record.resource_id} is underutilized (CPU: {cpu_utilization}%). Consider downsizing."
                    })
            
            # Check for idle resources
            if record.category == CostCategory.STORAGE:
                last_accessed = record.metadata.get("last_accessed")
                if last_accessed:
                    days_since_access = (datetime.utcnow() - last_accessed).days
                    if days_since_access > 90:
                        recommendations.append({
                            "type": "archive",
                            "resource_id": record.resource_id,
                            "cloud": record.cloud.value,
                            "category": record.category.value,
                            "current_cost": str(record.cost),
                            "potential_savings": str(record.cost * Decimal("0.7")),
                            "recommendation": f"Resource {record.resource_id} has not been accessed for {days_since_access} days. Consider archiving."
                        })
        
        return recommendations
    
    async def list_budgets(
        self,
        cloud: Optional[CloudProvider] = None,
        category: Optional[CostCategory] = None
    ) -> List[Budget]:
        """
        List budgets
        
        Args:
            cloud: Cloud provider (optional)
            category: Cost category (optional)
            
        Returns:
            List of budgets
        """
        budgets = list(self.budgets.values())
        
        if cloud:
            budgets = [b for b in budgets if b.cloud is None or b.cloud == cloud]
        
        if category:
            budgets = [b for b in budgets if b.category is None or b.category == category]
        
        return budgets
    
    async def get_budget_status(
        self,
        budget_id: str
    ) -> Dict[str, Any]:
        """
        Get budget status
        
        Args:
            budget_id: Budget ID
            
        Returns:
            Budget status
        """
        budget = self.budgets.get(budget_id)
        if not budget:
            return {"error": "Budget not found"}
        
        # Calculate current spend
        current_spend = await self._calculate_budget_spend(budget)
        
        # Calculate percentage
        percentage = float(current_spend / budget.amount) if budget.amount > 0 else 0
        
        # Determine status
        if percentage >= 1.0:
            status = "over_budget"
        elif percentage >= 0.95:
            status = "critical"
        elif percentage >= 0.8:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "budget_id": budget_id,
            "name": budget.name,
            "amount": str(budget.amount),
            "current_spend": str(current_spend),
            "remaining": str(budget.amount - current_spend),
            "percentage": percentage,
            "status": status,
            "alert_thresholds": budget.alert_thresholds
        }
    
    async def get_cost_analytics(self) -> Dict[str, Any]:
        """
        Get cost analytics
        
        Returns:
            Cost statistics
        """
        total_cost = sum(record.cost for record in self.cost_records.values())
        
        # By cloud
        by_cloud = {}
        for record in self.cost_records.values():
            cloud_name = record.cloud.value
            by_cloud[cloud_name] = by_cloud.get(cloud_name, Decimal("0")) + record.cost
        
        # By category
        by_category = {}
        for record in self.cost_records.values():
            category_name = record.category.value
            by_category[category_name] = by_category.get(category_name, Decimal("0")) + record.cost
        
        # Budget status
        budget_status = {}
        for budget_id, budget in self.budgets.items():
            current_spend = await self._calculate_budget_spend(budget)
            percentage = float(current_spend / budget.amount) if budget.amount > 0 else 0
            budget_status[budget_id] = {
                "amount": str(budget.amount),
                "spend": str(current_spend),
                "percentage": percentage
            }
        
        return {
            "total_cost": str(total_cost),
            "total_records": len(self.cost_records),
            "by_cloud": {k: str(v) for k, v in by_cloud.items()},
            "by_category": {k: str(v) for k, v in by_category.items()},
            "budget_status": budget_status,
            "total_budgets": len(self.budgets)
        }