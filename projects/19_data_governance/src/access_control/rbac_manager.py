"""
Role-Based Access Control (RBAC) Manager Module
===============================================
Manages enterprise security roles, permission grants, user assignments,
and role hierarchy evaluation for data access requests.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class Permission:
    """Represents a granular permission action."""
    name: str
    description: str = ""


@dataclass
class Role:
    """Represents a security role containing a set of permissions."""
    name: str
    permissions: Set[str] = field(default_factory=set)
    description: str = ""


@dataclass
class User:
    """Represents a system user or service account with assigned roles."""
    user_id: str
    username: str
    roles: Set[str] = field(default_factory=set)
    allowed_domains: Set[str] = field(default_factory=set)


class RBACManager:
    """
    Central Manager for Role-Based Access Control.
    """

    def __init__(self) -> None:
        self._roles: Dict[str, Role] = {}
        self._users: Dict[str, User] = {}
        self._init_default_roles()

    def _init_default_roles(self) -> None:
        """Initialize standard system roles."""
        self.create_role("DATA_ADMIN", {"read", "write", "delete", "grant_access", "manage_policy", "read_unmasked_pii"}, "Full admin access")
        self.create_role("DATA_ENGINEER", {"read", "write", "create_lineage", "read_masked_pii"}, "ETL and pipeline developer")
        self.create_role("DATA_ANALYST", {"read", "read_masked_pii"}, "Analytics user with masked PII view")
        self.create_role("DATA_STEWARD", {"read", "write_metadata", "classify_data", "tag_sensitivity"}, "Governance & metadata manager")
        self.create_role("DATA_VIEWER", {"read_public_only"}, "Restricted public viewer")

    def create_role(self, role_name: str, permissions: Set[str], description: str = "") -> Role:
        """Create or update a role with a set of permissions."""
        role = Role(name=role_name, permissions=set(permissions), description=description)
        self._roles[role_name] = role
        logger.info(f"Role '{role_name}' created with {len(permissions)} permissions.")
        return role

    def register_user(self, user_id: str, username: str, roles: Optional[Set[str]] = None, allowed_domains: Optional[Set[str]] = None) -> User:
        """Register a new user account."""
        user = User(
            user_id=user_id,
            username=username,
            roles=set(roles) if roles else {"DATA_VIEWER"},
            allowed_domains=set(allowed_domains) if allowed_domains else {"*"},
        )
        self._users[user_id] = user
        logger.info(f"User '{username}' [{user_id}] registered with roles: {user.roles}.")
        return user

    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user."""
        user = self._users.get(user_id)
        if not user or role_name not in self._roles:
            logger.warning(f"Failed to assign role '{role_name}' to user '{user_id}'.")
            return False

        user.roles.add(role_name)
        logger.info(f"Assigned role '{role_name}' to user '{user_id}'.")
        return True

    def revoke_role_from_user(self, user_id: str, role_name: str) -> bool:
        """Revoke a role from a user."""
        user = self._users.get(user_id)
        if not user or role_name not in user.roles:
            return False

        user.roles.remove(role_name)
        logger.info(f"Revoked role '{role_name}' from user '{user_id}'.")
        return True

    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Aggregate all permissions across all assigned user roles."""
        user = self._users.get(user_id)
        if not user:
            return set()

        permissions: Set[str] = set()
        for role_name in user.roles:
            role = self._roles.get(role_name)
            if role:
                permissions.update(role.permissions)

        return permissions

    def check_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if a user possesses a specific permission.
        
        Args:
            user_id: User identifier.
            permission: Permission string (e.g. "read_unmasked_pii").
            
        Returns:
            True if user has permission, else False.
        """
        user_perms = self.get_user_permissions(user_id)
        has_perm = permission in user_perms
        logger.debug(f"Permission check for user '{user_id}' on '{permission}': {has_perm}")
        return has_perm

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
