"""
Enterprise Authorization Service
Policy-based access control, RBAC, ABAC
"""

from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Effect(str, Enum):
    """Policy effect"""
    ALLOW = "allow"
    DENY = "deny"


class Action(str, Enum):
    """Standard actions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"
    APPROVE = "approve"


@dataclass
class Resource:
    """Resource model"""
    resource_id: str
    resource_type: str
    owner: str
    sensitivity: str
    classification: str
    attributes: Dict[str, Any]
    created_at: datetime


@dataclass
class Subject:
    """Subject (user/service) model"""
    subject_id: str
    subject_type: str  # user, service, group
    roles: List[str]
    attributes: Dict[str, Any]
    groups: List[str]


@dataclass
class Policy:
    """Authorization policy"""
    policy_id: str
    name: str
    description: str
    effect: Effect
    resources: List[str]
    actions: List[Action]
    conditions: Dict[str, Any]
    priority: int
    enabled: bool
    created_at: datetime


@dataclass
class AccessRequest:
    """Access request"""
    subject: Subject
    resource: Resource
    action: Action
    context: Dict[str, Any]


@dataclass
class AccessDecision:
    """Access decision"""
    allowed: bool
    effect: Effect
    policy_id: Optional[str]
    reason: str
    obligations: List[str]


class AuthorizationService:
    """
    Enterprise authorization service
    Supports RBAC, ABAC, and policy-based access control
    """

    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.role_permissions: Dict[str, Set[str]] = {}
        self.attribute_rules: List[Dict[str, Any]] = []

    async def check_access(self, request: AccessRequest) -> AccessDecision:
        """
        Check access request

        Args:
            request: Access request

        Returns:
            Access decision
        """
        # Get applicable policies
        applicable_policies = await self._get_applicable_policies(request)

        # Evaluate policies in priority order
        for policy in sorted(applicable_policies, key=lambda p: p.priority, reverse=True):
            if await self._evaluate_policy(policy, request):
                return AccessDecision(
                    allowed=policy.effect == Effect.ALLOW,
                    effect=policy.effect,
                    policy_id=policy.policy_id,
                    reason=policy.description,
                    obligations=[]
                )

        # Default deny
        return AccessDecision(
            allowed=False,
            effect=Effect.DENY,
            policy_id=None,
            reason="No matching policy found",
            obligations=[]
        )

    async def create_policy(self, policy: Policy) -> Policy:
        """
        Create authorization policy

        Args:
            policy: Policy to create

        Returns:
            Created policy
        """
        self.policies[policy.policy_id] = policy
        logger.info(f"Policy created - {policy.policy_id}")
        return policy

    async def grant_role(self, role: str, permissions: List[str]):
        """
        Grant permissions to role

        Args:
            role: Role name
            permissions: List of permissions
        """
        if role not in self.role_permissions:
            self.role_permissions[role] = set()

        self.role_permissions[role].update(permissions)
        logger.info(f"Permissions granted to role {role}")

    async def check_permission(self, role: str, permission: str) -> bool:
        """
        Check if role has permission

        Args:
            role: Role name
            permission: Permission to check

        Returns:
            True if has permission
        """
        return permission in self.role_permissions.get(role, set())

    async def add_attribute_rule(self, rule: Dict[str, Any]):
        """
        Add ABAC attribute rule

        Args:
            rule: Attribute rule
        """
        self.attribute_rules.append(rule)
        logger.info(f"Attribute rule added")

    async def _get_applicable_policies(self, request: AccessRequest) -> List[Policy]:
        """Get policies applicable to request"""
        applicable = []

        for policy in self.policies.values():
            if not policy.enabled:
                continue

            # Check resource match
            if "*" not in policy.resources and request.resource.resource_id not in policy.resources:
                continue

            # Check action match
            if Action.ADMIN not in policy.actions and request.action not in policy.actions:
                continue

            applicable.append(policy)

        return applicable

    async def _evaluate_policy(self, policy: Policy, request: AccessRequest) -> bool:
        """Evaluate policy against request"""
        # Evaluate conditions
        for condition_key, condition_value in policy.conditions.items():
            if not await self._evaluate_condition(condition_key, condition_value, request):
                return False

        return True

    async def _evaluate_condition(
        self,
        key: str,
        value: Any,
        request: AccessRequest
    ) -> bool:
        """Evaluate policy condition"""
        # Get attribute value
        subject_attr = request.subject.attributes.get(key)
        resource_attr = request.resource.attributes.get(key)
        context_attr = request.context.get(key)

        # StringMatch condition
        if isinstance(value, str):
            return (
                subject_attr == value or
                resource_attr == value or
                context_attr == value
            )

        # List condition (any match)
        if isinstance(value, list):
            return any(
                attr in value
                for attr in [subject_attr, resource_attr, context_attr]
                if attr is not None
            )

        # Dict condition (operator)
        if isinstance(value, dict):
            operator = value.get("operator")
            operand = value.get("value")

            if operator == "eq":
                return subject_attr == operand or resource_attr == operand
            elif operator == "neq":
                return subject_attr != operand and resource_attr != operand
            elif operator == "in":
                return subject_attr in operand or resource_attr in operand
            elif operator == "gt":
                return (subject_attr or 0) > operand
            elif operator == "lt":
                return (subject_attr or 0) < operand
            elif operator == "gte":
                return (subject_attr or 0) >= operand
            elif operator == "lte":
                return (subject_attr or 0) <= operand

        return False

    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """
        Get all permissions for user

        Args:
            user_id: User identifier

        Returns:
            Set of permissions
        """
        permissions = set()

        # Get user roles (simplified - in production, query identity service)
        user_roles = []  # await self.identity_service.get_user_roles(user_id)

        # Get permissions for each role
        for role in user_roles:
            permissions.update(self.role_permissions.get(role, set()))

        return permissions

    async def evaluate_abac(
        self,
        subject_attributes: Dict[str, Any],
        resource_attributes: Dict[str, Any],
        action: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate ABAC policy

        Args:
            subject_attributes: Subject attributes
            resource_attributes: Resource attributes
            action: Action to perform
            context: Request context

        Returns:
            True if allowed
        """
        for rule in self.attribute_rules:
            if not await self._evaluate_abac_rule(rule, subject_attributes, resource_attributes, action, context):
                return False

        return True

    async def _evaluate_abac_rule(
        self,
        rule: Dict[str, Any],
        subject_attrs: Dict[str, Any],
        resource_attrs: Dict[str, Any],
        action: str,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate single ABAC rule"""
        # Check subject match
        if "subject_match" in rule:
            for key, value in rule["subject_match"].items():
                if subject_attrs.get(key) != value:
                    return True  # Rule doesn't apply

        # Check resource match
        if "resource_match" in rule:
            for key, value in rule["resource_match"].items():
                if resource_attrs.get(key) != value:
                    return True  # Rule doesn't apply

        # Check action
        if "action" in rule and action not in rule["action"]:
            return True  # Rule doesn't apply

        # Evaluate condition
        if "condition" in rule:
            condition = rule["condition"]
            result = await self._evaluate_condition(
                condition.get("attribute"),
                condition.get("value"),
                None
            )
            return result

        return True


class RBACService:
    """
    Role-Based Access Control service
    """

    def __init__(self, authorization_service: AuthorizationService):
        self.authz_service = authorization_service
        self.role_hierarchy: Dict[str, List[str]] = {}

    async def assign_role(self, user_id: str, role: str):
        """
        Assign role to user

        Args:
            user_id: User identifier
            role: Role to assign
        """
        # In production, persist to database
        logger.info(f"Role {role} assigned to user {user_id}")

    async def revoke_role(self, user_id: str, role: str):
        """
        Revoke role from user

        Args:
            user_id: User identifier
            role: Role to revoke
        """
        # In production, persist to database
        logger.info(f"Role {role} revoked from user {user_id}")

    async def check_role_permission(self, role: str, permission: str) -> bool:
        """
        Check if role has permission

        Args:
            role: Role name
            permission: Permission to check

        Returns:
            True if has permission
        """
        return await self.authz_service.check_permission(role, permission)

    async def get_inherited_roles(self, role: str) -> List[str]:
        """
        Get inherited roles (role hierarchy)

        Args:
            role: Role name

        Returns:
            List of inherited roles
        """
        return self.role_hierarchy.get(role, [])

    async def create_role_hierarchy(self, role: str, inherits: List[str]):
        """
        Create role hierarchy

        Args:
            role: Role name
            inherits: List of roles to inherit
        """
        self.role_hierarchy[role] = inherits
        logger.info(f"Role hierarchy created for {role}")