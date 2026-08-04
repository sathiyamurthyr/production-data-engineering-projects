"""
Role-Based Access Control (RBAC) Implementation
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class PermissionType(str, Enum):
    """Permission types"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"
    APPROVE = "approve"
    AUDIT = "audit"
    MANAGE = "manage"


@dataclass
class Role:
    """Role definition"""
    role_id: str
    name: str
    description: str
    permissions: Set[str]
    inherits: List[str]
    attributes: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class RoleAssignment:
    """Role assignment to user"""
    assignment_id: str
    user_id: str
    role_id: str
    assigned_by: str
    assigned_at: datetime
    expires_at: Optional[datetime]
    justification: str


class RBACManager:
    """
    Enterprise RBAC manager
    """

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.assignments: List[RoleAssignment] = {}
        self.permission_registry: Dict[str, PermissionType] = {}

    async def create_role(
        self,
        role_id: str,
        name: str,
        description: str,
        permissions: List[str],
        inherits: List[str] = None
    ) -> Role:
        """
        Create new role

        Args:
            role_id: Role identifier
            name: Role name
            description: Role description
            permissions: List of permissions
            inherits: List of parent roles

        Returns:
            Created role
        """
        now = datetime.utcnow()

        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            permissions=set(permissions),
            inherits=inherits or [],
            attributes={},
            created_at=now,
            updated_at=now
        )

        self.roles[role_id] = role
        logger.info(f"Role created - {role_id}")

        return role

    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str,
        justification: str,
        expires_at: Optional[datetime] = None
    ) -> RoleAssignment:
        """
        Assign role to user

        Args:
            user_id: User identifier
            role_id: Role to assign
            assigned_by: Who assigned the role
            justification: Reason for assignment
            expires_at: Optional expiration

        Returns:
            Role assignment
        """
        if role_id not in self.roles:
            raise ValueError("Role does not exist")

        assignment = RoleAssignment(
            assignment_id=f"{user_id}-{role_id}-{datetime.utcnow().timestamp()}",
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow(),
            expires_at=expires_at,
            justification=justification
        )

        self.assignments[assignment.assignment_id] = assignment
        logger.info(f"Role {role_id} assigned to user {user_id}")

        return assignment

    async def revoke_role(self, user_id: str, role_id: str):
        """
        Revoke role from user

        Args:
            user_id: User identifier
            role_id: Role to revoke
        """
        # Find and remove assignment
        to_remove = [
            aid for aid, a in self.assignments.items()
            if a.user_id == user_id and a.role_id == role_id
        ]

        for aid in to_remove:
            del self.assignments[aid]
            logger.info(f"Role {role_id} revoked from user {user_id}")

    async def get_user_roles(self, user_id: str) -> List[Role]:
        """
        Get all roles for user (including inherited)

        Args:
            user_id: User identifier

        Returns:
            List of roles
        """
        # Get direct assignments
        user_role_ids = [
            a.role_id for a in self.assignments.values()
            if a.user_id == user_id
        ]

        # Expand with inherited roles
        expanded_roles = set()
        await self._expand_roles(user_role_ids, expanded_roles)

        # Get role objects
        roles = [self.roles[rid] for rid in expanded_roles if rid in self.roles]

        return roles

    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """
        Get all permissions for user

        Args:
            user_id: User identifier

        Returns:
            Set of permissions
        """
        permissions = set()

        # Get all roles
        roles = await self.get_user_roles(user_id)

        # Collect permissions
        for role in roles:
            permissions.update(role.permissions)

        return permissions

    async def check_permission(
        self,
        user_id: str,
        permission: str
    ) -> bool:
        """
        Check if user has permission

        Args:
            user_id: User identifier
            permission: Permission to check

        Returns:
            True if user has permission
        """
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions

    async def add_permission_to_role(
        self,
        role_id: str,
        permission: str
    ):
        """
        Add permission to role

        Args:
            role_id: Role identifier
            permission: Permission to add
        """
        if role_id not in self.roles:
            raise ValueError("Role does not exist")

        self.roles[role_id].permissions.add(permission)
        self.roles[role_id].updated_at = datetime.utcnow()

        logger.info(f"Permission {permission} added to role {role_id}")

    async def remove_permission_from_role(
        self,
        role_id: str,
        permission: str
    ):
        """
        Remove permission from role

        Args:
            role_id: Role identifier
            permission: Permission to remove
        """
        if role_id not in self.roles:
            raise ValueError("Role does not exist")

        self.roles[role_id].permissions.discard(permission)
        self.roles[role_id].updated_at = datetime.utcnow()

        logger.info(f"Permission {permission} removed from role {role_id}")

    async def create_role_hierarchy(
        self,
        parent_role_id: str,
        child_role_id: str
    ):
        """
        Create role hierarchy (child inherits from parent)

        Args:
            parent_role_id: Parent role
            child_role_id: Child role
        """
        if parent_role_id not in self.roles:
            raise ValueError("Parent role does not exist")

        if child_role_id not in self.roles:
            raise ValueError("Child role does not exist")

        self.roles[child_role_id].inherits.append(parent_role_id)
        self.roles[child_role_id].updated_at = datetime.utcnow()

        logger.info(f"Role hierarchy created: {child_role_id} inherits {parent_role_id}")

    async def _expand_roles(
        self,
        role_ids: List[str],
        expanded: Set[str]
    ):
        """
        Recursively expand role hierarchy

        Args:
            role_ids: List of role IDs
            expanded: Set of expanded role IDs
        """
        for role_id in role_ids:
            if role_id in expanded:
                continue

            expanded.add(role_id)

            if role_id in self.roles:
                # Add inherited roles
                for inherited_role in self.roles[role_id].inherits:
                    if inherited_role not in expanded:
                        await self._expand_roles([inherited_role], expanded)

    async def validate_role_assignment(
        self,
        user_id: str,
        role_id: str
    ) -> bool:
        """
        Validate role assignment (separation of duties, etc.)

        Args:
            user_id: User identifier
            role_id: Role to validate

        Returns:
            True if valid assignment
        """
        # Get existing roles
        existing_roles = await self.get_user_roles(user_id)

        # Check for conflicting roles
        conflicts = self._check_role_conflicts(role_id, [r.role_id for r in existing_roles])

        if conflicts:
            logger.warning(f"Role assignment conflict detected: {conflicts}")
            return False

        return True

    def _check_role_conflicts(
        self,
        role_id: str,
        existing_role_ids: List[str]
    ) -> List[str]:
        """
        Check for role conflicts

        Args:
            role_id: Role to check
            existing_role_ids: Existing roles

        Returns:
            List of conflicting roles
        """
        conflicts = []

        # Define conflicting role pairs
        conflict_pairs = [
            ("admin", "auditor"),
            ("developer", "production_admin"),
            ("finance", "procurement"),
            ("security", "auditee"),
        ]

        for existing_role in existing_role_ids:
            for conflict_pair in conflict_pairs:
                if (
                    (role_id == conflict_pair[0] and existing_role == conflict_pair[1]) or
                    (role_id == conflict_pair[1] and existing_role == conflict_pair[0])
                ):
                    conflicts.append(existing_role)

        return conflicts

    async def audit_role_assignments(self) -> Dict[str, Any]:
        """
        Audit all role assignments

        Returns:
            Audit report
        """
        report = {
            "total_assignments": len(self.assignments),
            "total_roles": len(self.roles),
            "assignments_by_role": {},
            "expired_assignments": []
        }

        # Count by role
        for assignment in self.assignments.values():
            role_id = assignment.role_id
            report["assignments_by_role"][role_id] = \
                report["assignments_by_role"].get(role_id, 0) + 1

            # Check expiration
            if assignment.expires_at and assignment.expires_at < datetime.utcnow():
                report["expired_assignments"].append(assignment.assignment_id)

        return report