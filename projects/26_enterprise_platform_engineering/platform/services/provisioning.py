"""
Provisioning Service
Manages self-service infrastructure provisioning and workflows
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import uuid
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://platform:platform@platform-postgres:5432/platform"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ============================================================================
# Enums
# ============================================================================

class ProvisioningStatus(str, Enum):
    """Provisioning request status."""
    PENDING = "pending"
    VALIDATING = "validating"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


class ApprovalStatus(str, Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ============================================================================
# Database Models
# ============================================================================

class ProvisioningRequestModel(Base):
    """Provisioning request database model."""
    __tablename__ = "provisioning_requests"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    template_id = Column(String, nullable=False, index=True)
    variables = Column(JSON, nullable=False)
    status = Column(String, default=ProvisioningStatus.PENDING.value, index=True)
    environment = Column(String, nullable=False, index=True)
    team = Column(String, nullable=False, index=True)
    requested_by = Column(String, nullable=False, index=True)
    approved_by = Column(String)
    approval_id = Column(String, index=True)
    terraform_config = Column(JSON)
    kubernetes_manifests = Column(JSON)
    output = Column(JSON)
    error_message = Column(Text)
    estimated_time = Column(Integer)  # seconds
    actual_time = Column(Integer)  # seconds
    cost_estimate = Column(Float)
    actual_cost = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)


class ApprovalModel(Base):
    """Approval request database model."""
    __tablename__ = "approvals"

    id = Column(String, primary_key=True)
    provisioning_id = Column(String, nullable=False, index=True)
    status = Column(String, default=ApprovalStatus.PENDING.value, index=True)
    requested_from = Column(String, nullable=False)
    requested_by = Column(String, nullable=False)
    comment = Column(Text)
    approved_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProvisioningEventModel(Base):
    """Provisioning event database model."""
    __tablename__ = "provisioning_events"

    id = Column(String, primary_key=True)
    provisioning_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)  # status_change, approval, error, etc.
    message = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ============================================================================
# Pydantic Models
# ============================================================================

class ProvisioningRequest(BaseModel):
    """Provisioning request model."""
    id: str
    name: str
    template_id: str
    variables: Dict[str, Any]
    status: ProvisioningStatus
    environment: str
    team: str
    requested_by: str
    approved_by: Optional[str] = None
    approval_id: Optional[str] = None
    terraform_config: Optional[Dict[str, Any]] = None
    kubernetes_manifests: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    estimated_time: Optional[int] = None
    actual_time: Optional[int] = None
    cost_estimate: Optional[float] = None
    actual_cost: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class Approval(BaseModel):
    """Approval model."""
    id: str
    provisioning_id: str
    status: ApprovalStatus
    requested_from: str
    requested_by: str
    comment: Optional[str] = None
    approved_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime


class ProvisioningEvent(BaseModel):
    """Provisioning event model."""
    id: str
    provisioning_id: str
    event_type: str
    message: str
    metadata: Dict[str, Any]
    created_at: datetime


class ProvisioningCreate(BaseModel):
    """Provisioning creation request."""
    name: str
    template_id: str
    variables: Dict[str, Any]
    environment: str
    team: str


class ProvisioningResponse(BaseModel):
    """Provisioning response model."""
    provisioning_id: Optional[str]
    status: str
    approval_id: Optional[str] = None
    message: str
    estimated_time: Optional[int] = None
    created_at: str


class ApprovalRequest(BaseModel):
    """Approval request model."""
    comment: Optional[str] = None


class ValidationResult(BaseModel):
    """Validation result."""
    valid: bool
    errors: List[Dict[str, str]]


# ============================================================================
# Provisioning Service
# ============================================================================

class ProvisioningService:
    """Provisioning management service."""

    def __init__(self):
        self.requests: Dict[str, ProvisioningRequest] = {}
        self.approvals: Dict[str, Approval] = {}
        self.events: Dict[str, List[ProvisioningEvent]] = {}

    async def initialize(self):
        """Initialize provisioning service."""
        logger.info("Initializing provisioning service...")

        # Create database tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Load pending requests
        await self._load_requests()

        logger.info(f"Provisioning service initialized with {len(self.requests)} requests")

    async def _load_requests(self):
        """Load pending requests from database."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ProvisioningRequestModel).where(
                    ProvisioningRequestModel.status.in_([
                        ProvisioningStatus.PENDING.value,
                        ProvisioningStatus.PROVISIONING.value
                    ])
                )
            )
            requests = result.scalars().all()

            for req in requests:
                request = ProvisioningRequest(
                    id=req.id,
                    name=req.name,
                    template_id=req.template_id,
                    variables=req.variables,
                    status=ProvisioningStatus(req.status),
                    environment=req.environment,
                    team=req.team,
                    requested_by=req.requested_by,
                    approved_by=req.approved_by,
                    approval_id=req.approval_id,
                    terraform_config=req.terraform_config,
                    kubernetes_manifests=req.kubernetes_manifests,
                    output=req.output,
                    error_message=req.error_message,
                    estimated_time=req.estimated_time,
                    actual_time=req.actual_time,
                    cost_estimate=req.cost_estimate,
                    actual_cost=req.actual_cost,
                    created_at=req.created_at,
                    updated_at=req.updated_at,
                    completed_at=req.completed_at
                )
                self.requests[req.id] = request

    async def health_check(self) -> Dict[str, str]:
        """Health check for provisioning service."""
        try:
            # Test database connection
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                await session.execute(select(ProvisioningRequestModel).limit(1))

            return {
                "status": "healthy",
                "pending_requests": str(sum(1 for r in self.requests.values() if r.status == ProvisioningStatus.PENDING)),
                "active_provisions": str(sum(1 for r in self.requests.values() if r.status == ProvisioningStatus.PROVISIONING))
            }
        except Exception as e:
            logger.error(f"Provisioning service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def validate_request(self, request: ProvisioningCreate) -> ValidationResult:
        """
        Validate provisioning request.
        
        Args:
            request: Provisioning creation request
            
        Returns:
            Validation result
        """
        errors = []

        # Validate environment
        valid_environments = ["dev", "staging", "prod"]
        if request.environment not in valid_environments:
            errors.append({
                "field": "environment",
                "message": f"Invalid environment. Must be one of: {valid_environments}",
                "code": "INVALID_ENVIRONMENT"
            })

        # Validate team
        if not request.team or len(request.team) < 2:
            errors.append({
                "field": "team",
                "message": "Team name must be at least 2 characters",
                "code": "INVALID_TEAM"
            })

        # Validate name
        if not request.name or len(request.name) < 3:
            errors.append({
                "field": "name",
                "message": "Name must be at least 3 characters",
                "code": "INVALID_NAME"
            })

        # Validate template exists (would check template engine)
        # This is a placeholder validation
        if not request.template_id:
            errors.append({
                "field": "template_id",
                "message": "Template ID is required",
                "code": "TEMPLATE_REQUIRED"
            })

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )

    async def provision(
        self,
        request: ProvisioningCreate,
        user: Optional[Any] = None
    ) -> ProvisioningRequest:
        """
        Provision a new resource.
        
        Args:
            request: Provisioning creation request
            user: User requesting provisioning
            
        Returns:
            Created provisioning request
        """
        provisioning_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Create provisioning request
        provisioning_request = ProvisioningRequest(
            id=provisioning_id,
            name=request.name,
            template_id=request.template_id,
            variables=request.variables,
            status=ProvisioningStatus.PROVISIONING,
            environment=request.environment,
            team=request.team,
            requested_by=user.username if user else "system",
            estimated_time=300,  # 5 minutes
            cost_estimate=100.0,
            created_at=now,
            updated_at=now
        )

        # Save to database
        async with AsyncSessionLocal() as session:
            model = ProvisioningRequestModel(
                id=provisioning_id,
                name=request.name,
                template_id=request.template_id,
                variables=request.variables,
                status=ProvisioningStatus.PROVISIONING.value,
                environment=request.environment,
                team=request.team,
                requested_by=user.username if user else "system",
                estimated_time=300,
                cost_estimate=100.0,
                created_at=now,
                updated_at=now
            )
            session.add(model)
            await session.commit()

        # Add to cache
        self.requests[provisioning_id] = provisioning_request

        # Record event
        await self._record_event(
            provisioning_id=provisioning_id,
            event_type="provisioning_started",
            message=f"Provisioning started for {request.name}"
        )

        # TODO: Start actual provisioning workflow
        # This would involve:
        # 1. Rendering template with variables
        # 2. Running Terraform to provision infrastructure
        # 3. Deploying applications
        # 4. Running health checks

        logger.info(f"Started provisioning: {provisioning_id} - {request.name}")
        return provisioning_request

    async def get_status(self, provisioning_id: str) -> Optional[ProvisioningRequest]:
        """
        Get provisioning status.
        
        Args:
            provisioning_id: Provisioning request ID
            
        Returns:
            Provisioning request or None if not found
        """
        return self.requests.get(provisioning_id)

    async def list_requests(
        self,
        user: Optional[Any] = None,
        status: Optional[str] = None,
        team: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProvisioningRequest]:
        """
        List provisioning requests.
        
        Args:
            user: Current user
            status: Filter by status
            team: Filter by team
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of provisioning requests
        """
        requests = list(self.requests.values())

        # Apply filters
        if status:
            requests = [r for r in requests if r.status.value == status]

        if team:
            requests = [r for r in requests if r.team == team]

        # Sort by created_at descending
        requests.sort(key=lambda r: r.created_at, reverse=True)

        # Paginate
        return requests[offset:offset + limit]

    async def cancel(self, provisioning_id: str, user: Any) -> bool:
        """
        Cancel provisioning request.
        
        Args:
            provisioning_id: Provisioning request ID
            user: User requesting cancellation
            
        Returns:
            True if cancelled, False if not found
        """
        request = self.requests.get(provisioning_id)
        if not request:
            return False

        # Check if can be cancelled
        if request.status not in [
            ProvisioningStatus.PENDING,
            ProvisioningStatus.PROVISIONING
        ]:
            raise ValueError(f"Cannot cancel provisioning in status: {request.status}")

        # Update status
        request.status = ProvisioningStatus.CANCELLED
        request.updated_at = datetime.utcnow()

        # Update database
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            stmt = update(ProvisioningRequestModel).where(
                ProvisioningRequestModel.id == provisioning_id
            ).values(
                status=ProvisioningStatus.CANCELLED.value,
                updated_at=datetime.utcnow()
            )
            await session.execute(stmt)
            await session.commit()

        # Record event
        await self._record_event(
            provisioning_id=provisioning_id,
            event_type="provisioning_cancelled",
            message=f"Provisioning cancelled by {user.username}"
        )

        logger.info(f"Cancelled provisioning: {provisioning_id}")
        return True

    async def create_approval_request(
        self,
        provisioning_request: ProvisioningCreate,
        user: Any
    ) -> Approval:
        """
        Create approval request.
        
        Args:
            provisioning_request: Provisioning request
            user: User requesting approval
            
        Returns:
            Created approval
        """
        # TODO: Determine who should approve based on policies
        # For now, approve from team lead
        approver = "team-lead"  # This would be dynamic

        approval_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=48)  # 48 hours to approve

        # Create approval
        approval = Approval(
            id=approval_id,
            provisioning_id="",  # Will be set when provisioning is created
            status=ApprovalStatus.PENDING,
            requested_from=approver,
            requested_by=user.username if user else "system",
            expires_at=expires_at,
            created_at=now
        )

        # Save to database
        async with AsyncSessionLocal() as session:
            model = ApprovalModel(
                id=approval_id,
                provisioning_id="",
                status=ApprovalStatus.PENDING.value,
                requested_from=approver,
                requested_by=user.username if user else "system",
                expires_at=expires_at,
                created_at=now
            )
            session.add(model)
            await session.commit()

        # Add to cache
        self.approvals[approval_id] = approval

        logger.info(f"Created approval request: {approval_id}")
        return approval

    async def approve(
        self,
        approval_id: str,
        user: Any,
        comment: Optional[str] = None
    ) -> bool:
        """
        Approve provisioning request.
        
        Args:
            approval_id: Approval ID
            user: User approving
            comment: Optional comment
            
        Returns:
            True if approved, False if not found
        """
        approval = self.approvals.get(approval_id)
        if not approval:
            return False

        # Check if user is authorized
        if approval.requested_from != user.username:
            raise ValueError(f"User {user.username} is not authorized to approve this request")

        # Check if expired
        if datetime.utcnow() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            return False

        # Update approval
        approval.status = ApprovalStatus.APPROVED
        approval.approved_at = datetime.utcnow()
        approval.comment = comment

        # Update database
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            stmt = update(ApprovalModel).where(ApprovalModel.id == approval_id).values(
                status=ApprovalStatus.APPROVED.value,
                approved_at=datetime.utcnow(),
                comment=comment
            )
            await session.execute(stmt)
            await session.commit()

        # Update provisioning request
        provisioning_id = approval.provisioning_id
        if provisioning_id:
            request = self.requests.get(provisioning_id)
            if request:
                request.status = ProvisioningStatus.APPROVED
                request.approved_by = user.username
                request.updated_at = datetime.utcnow()

        # Record event
        await self._record_event(
            provisioning_id=provisioning_id,
            event_type="provisioning_approved",
            message=f"Provisioning approved by {user.username}"
        )

        logger.info(f"Approved: {approval_id}")
        return True

    async def reject(
        self,
        approval_id: str,
        user: Any,
        comment: Optional[str] = None
    ) -> bool:
        """
        Reject provisioning request.
        
        Args:
            approval_id: Approval ID
            user: User rejecting
            comment: Rejection reason
            
        Returns:
            True if rejected, False if not found
        """
        approval = self.approvals.get(approval_id)
        if not approval:
            return False

        # Check if user is authorized
        if approval.requested_from != user.username:
            raise ValueError(f"User {user.username} is not authorized to reject this request")

        # Update approval
        approval.status = ApprovalStatus.REJECTED
        approval.approved_at = datetime.utcnow()
        approval.comment = comment

        # Update database
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            stmt = update(ApprovalModel).where(ApprovalModel.id == approval_id).values(
                status=ApprovalStatus.REJECTED.value,
                approved_at=datetime.utcnow(),
                comment=comment
            )
            await session.execute(stmt)
            await session.commit()

        # Update provisioning request
        provisioning_id = approval.provisioning_id
        if provisioning_id:
            request = self.requests.get(provisioning_id)
            if request:
                request.status = ProvisioningStatus.REJECTED
                request.error_message = comment
                request.updated_at = datetime.utcnow()

        # Record event
        await self._record_event(
            provisioning_id=provisioning_id,
            event_type="provisioning_rejected",
            message=f"Provisioning rejected by {user.username}: {comment}"
        )

        logger.info(f"Rejected: {approval_id}")
        return True

    async def list_pending_approvals(self, user: Any) -> List[Approval]:
        """
        List pending approvals for user.
        
        Args:
            user: Current user
            
        Returns:
            List of pending approvals
        """
        pending = []

        for approval in self.approvals.values():
            if (
                approval.status == ApprovalStatus.PENDING
                and approval.requested_from == user.username
                and approval.expires_at > datetime.utcnow()
            ):
                pending.append(approval)

        return pending

    async def _record_event(
        self,
        provisioning_id: str,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record provisioning event."""
        event_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Save to database
        async with AsyncSessionLocal() as session:
            model = ProvisioningEventModel(
                id=event_id,
                provisioning_id=provisioning_id,
                event_type=event_type,
                message=message,
                metadata=metadata or {},
                created_at=now
            )
            session.add(model)
            await session.commit()

        # Add to cache
        if provisioning_id not in self.events:
            self.events[provisioning_id] = []

        event = ProvisioningEvent(
            id=event_id,
            provisioning_id=provisioning_id,
            event_type=event_type,
            message=message,
            metadata=metadata or {},
            created_at=now
        )
        self.events[provisioning_id].append(event)

        logger.debug(f"Recorded event: {event_type} for {provisioning_id}")

    async def get_events(self, provisioning_id: str) -> List[ProvisioningEvent]:
        """
        Get events for provisioning request.
        
        Args:
            provisioning_id: Provisioning request ID
            
        Returns:
            List of events
        """
        return self.events.get(provisioning_id, [])

    async def update_status(
        self,
        provisioning_id: str,
        status: ProvisioningStatus,
        message: Optional[str] = None
    ):
        """
        Update provisioning status.
        
        Args:
            provisioning_id: Provisioning request ID
            status: New status
            message: Optional status message
        """
        request = self.requests.get(provisioning_id)
        if not request:
            return

        request.status = status
        request.updated_at = datetime.utcnow()

        if status == ProvisioningStatus.COMPLETED:
            request.completed_at = datetime.utcnow()
            request.actual_time = int((request.updated_at - request.created_at).total_seconds())

        # Update database
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            stmt = update(ProvisioningRequestModel).where(
                ProvisioningRequestModel.id == provisioning_id
            ).values(
                status=status.value,
                updated_at=datetime.utcnow(),
                completed_at=request.completed_at
            )
            await session.execute(stmt)
            await session.commit()

        # Record event
        await self._record_event(
            provisioning_id=provisioning_id,
            event_type="status_change",
            message=f"Status changed to {status.value}: {message or ''}"
        )

        logger.info(f"Updated provisioning {provisioning_id} status to {status.value}")

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get provisioning statistics.
        
        Returns:
            Statistics dictionary
        """
        total = len(self.requests)
        by_status = {}
        by_team = {}
        by_environment = {}

        for request in self.requests.values():
            # Count by status
            status = request.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # Count by team
            by_team[request.team] = by_team.get(request.team, 0) + 1

            # Count by environment
            by_environment[request.environment] = by_environment.get(request.environment, 0) + 1

        # Calculate average provisioning time
        completed = [r for r in self.requests.values() if r.actual_time is not None]
        avg_time = sum(r.actual_time for r in completed) / len(completed) if completed else 0

        return {
            "total_requests": total,
            "by_status": by_status,
            "by_team": by_team,
            "by_environment": by_environment,
            "average_provisioning_time_seconds": avg_time,
            "success_rate": by_status.get("completed", 0) / total if total > 0 else 0
        }