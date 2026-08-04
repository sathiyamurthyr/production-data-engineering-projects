"""
Firewall Policy Service for Cross-Cloud Platform

This module provides unified firewall management across Azure and AWS.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RuleAction(str, Enum):
    """Rule actions"""
    ALLOW = "allow"
    DENY = "deny"
    LOG = "log"


class FirewallRule(BaseModel):
    """Firewall rule"""
    rule_id: str
    name: str
    priority: int
    action: RuleAction
    source: str
    destination: str
    port: str
    protocol: str
    description: str
    enabled: bool = True
    created_at: datetime
    updated_at: datetime


class FirewallPolicy(BaseModel):
    """Firewall policy"""
    policy_id: str
    name: str
    description: str
    cloud: str
    region: str
    rules: List[FirewallRule]
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class FirewallPolicyService:
    """
    Cross-cloud firewall policy service
    
    This service provides:
    - Firewall rule management
    - Policy enforcement
    - Network security groups
    - Access control lists
    """
    
    def __init__(self, config: Dict):
        """
        Initialize firewall policy service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.policies: Dict[str, FirewallPolicy] = {}
        self.rules: Dict[str, FirewallRule] = {}
        
        logger.info("Firewall Policy Service initialized")
    
    async def create_policy(
        self,
        policy_id: str,
        name: str,
        description: str,
        cloud: str,
        region: str,
        rules: List[FirewallRule],
        properties: Optional[Dict[str, Any]] = None
    ) -> FirewallPolicy:
        """
        Create firewall policy
        
        Args:
            policy_id: Policy ID
            name: Policy name
            description: Policy description
            cloud: Cloud provider
            region: Cloud region
            rules: Firewall rules
            properties: Additional properties
            
        Returns:
            Firewall policy
        """
        logger.info(f"Creating firewall policy: {policy_id}")
        
        if policy_id in self.policies:
            raise ValueError(f"Policy already exists: {policy_id}")
        
        policy = FirewallPolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            cloud=cloud,
            region=region,
            rules=rules,
            properties=properties or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.policies[policy_id] = policy
        
        # Store rules
        for rule in rules:
            self.rules[rule.rule_id] = rule
        
        logger.info(f"Firewall policy created: {policy_id}")
        return policy
    
    async def get_policy(self, policy_id: str) -> Optional[FirewallPolicy]:
        """
        Get firewall policy by ID
        
        Args:
            policy_id: Policy ID
            
        Returns:
            Firewall policy if found, None otherwise
        """
        return self.policies.get(policy_id)
    
    async def add_rule(
        self,
        policy_id: str,
        rule: FirewallRule
    ) -> Optional[FirewallPolicy]:
        """
        Add rule to firewall policy
        
        Args:
            policy_id: Policy ID
            rule: Firewall rule
            
        Returns:
            Updated firewall policy
        """
        policy = self.policies.get(policy_id)
        if not policy:
            logger.warning(f"Firewall policy not found: {policy_id}")
            return None
        
        # Add rule
        policy.rules.append(rule)
        policy.updated_at = datetime.utcnow()
        
        # Store rule
        self.rules[rule.rule_id] = rule
        
        logger.info(f"Rule added to policy: {rule.rule_id}")
        return policy
    
    async def evaluate_request(
        self,
        source: str,
        destination: str,
        port: str,
        protocol: str,
        cloud: str
    ) -> Dict[str, Any]:
        """
        Evaluate network request against firewall policies
        
        Args:
            source: Source address
            destination: Destination address
            port: Port
            protocol: Protocol
            cloud: Cloud provider
            
        Returns:
            Evaluation result
        """
        # Get policies for cloud
        policies = [p for p in self.policies.values() if p.cloud == cloud]
        
        # Sort rules by priority
        all_rules = []
        for policy in policies:
            all_rules.extend(policy.rules)
        
        all_rules.sort(key=lambda r: r.priority)
        
        # Evaluate rules
        for rule in all_rules:
            if not rule.enabled:
                continue
            
            # Check if rule matches
            if self._rule_matches(rule, source, destination, port, protocol):
                return {
                    "allowed": rule.action == RuleAction.ALLOW,
                    "action": rule.action.value,
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "policy_id": rule.rule_id.split("-")[0]
                }
        
        # Default deny
        return {
            "allowed": False,
            "action": "deny",
            "rule_id": None,
            "rule_name": "default-deny",
            "policy_id": None
        }
    
    def _rule_matches(
        self,
        rule: FirewallRule,
        source: str,
        destination: str,
        port: str,
        protocol: str
    ) -> bool:
        """
        Check if rule matches request
        
        Args:
            rule: Firewall rule
            source: Source address
            destination: Destination address
            port: Port
            protocol: Protocol
            
        Returns:
            True if matches, False otherwise
        """
        # Simplified matching
        # In real implementation, use proper IP and port matching
        
        if rule.source != "*" and rule.source != source:
            return False
        
        if rule.destination != "*" and rule.destination != destination:
            return False
        
        if rule.port != "*" and rule.port != port:
            return False
        
        if rule.protocol != "*" and rule.protocol != protocol:
            return False
        
        return True
    
    async def list_policies(
        self,
        cloud: Optional[str] = None
    ) -> List[FirewallPolicy]:
        """
        List firewall policies
        
        Args:
            cloud: Cloud provider filter
            
        Returns:
            List of firewall policies
        """
        policies = list(self.policies.values())
        
        if cloud:
            policies = [p for p in policies if p.cloud == cloud]
        
        return policies
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get firewall analytics
        
        Returns:
            Firewall statistics
        """
        total_policies = len(self.policies)
        total_rules = len(self.rules)
        
        # By cloud
        by_cloud = {}
        for policy in self.policies.values():
            cloud = policy.cloud
            by_cloud[cloud] = by_cloud.get(cloud, 0) + 1
        
        # By action
        by_action = {}
        for rule in self.rules.values():
            action = rule.action.value
            by_action[action] = by_action.get(action, 0) + 1
        
        # Enabled vs disabled
        enabled = len([r for r in self.rules.values() if r.enabled])
        disabled = len([r for r in self.rules.values() if not r.enabled])
        
        return {
            "total_policies": total_policies,
            "total_rules": total_rules,
            "enabled_rules": enabled,
            "disabled_rules": disabled,
            "by_cloud": by_cloud,
            "by_action": by_action
        }