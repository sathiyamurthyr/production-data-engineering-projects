"""
SSO Provider for Cross-Cloud Authentication

This module provides Single Sign-On (SSO) capabilities across Azure and AWS.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import secrets
import hashlib
import base64
from urllib.parse import urlencode

from pydantic import BaseModel, Field
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .identity_federation import CloudProvider, UserIdentity, IdentityProvider

logger = logging.getLogger(__name__)


class SSOSession(BaseModel):
    """SSO session information"""
    session_id: str
    user_id: str
    provider_id: str
    issued_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    is_valid: bool = True


class SAMLAssertion(BaseModel):
    """SAML assertion for federation"""
    assertion_id: str
    session_id: str
    user_email: str
    user_name: str
    roles: List[str]
    issuer: str
    audience: str
    subject: str
    conditions: Dict[str, datetime]
    issued_at: datetime
    expires_at: datetime


class SSOProvider:
    """
    Single Sign-On provider for cross-cloud authentication
    
    This service provides:
    - SAML 2.0 SSO across Azure and AWS
    - Session management
    - Token validation and refresh
    - Cross-cloud authentication
    """
    
    def __init__(self, config: Dict):
        """
        Initialize SSO provider
        
        Args:
            config: Configuration dictionary containing:
                - azure_tenant_id: Azure AD tenant ID
                - azure_client_id: Azure AD application client ID
                - aws_saml_entity_id: AWS SAML entity ID
                - session_timeout: Session timeout in minutes
        """
        self.config = config
        self.sessions: Dict[str, SSOSession] = {}
        self.saml_assertions: Dict[str, SAMLAssertion] = {}
        
        # Session configuration
        self.session_timeout = config.get("session_timeout", 60)  # minutes
        
        # Generate or load signing key
        self._signing_key = self._generate_signing_key()
        
        logger.info("SSO Provider initialized")
    
    def _generate_signing_key(self) -> rsa.RSAPrivateKey:
        """Generate RSA key for SAML signing"""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
    
    def create_saml_assertion(
        self,
        user: UserIdentity,
        provider: IdentityProvider,
        target_cloud: CloudProvider
    ) -> SAMLAssertion:
        """
        Create SAML assertion for user
        
        Args:
            user: User identity
            provider: Identity provider
            target_cloud: Target cloud provider
            
        Returns:
            SAML assertion
        """
        logger.info(f"Creating SAML assertion for user {user.user_id}")
        
        # Generate assertion ID
        assertion_id = f"assertion-{secrets.token_urlsafe(32)}"
        
        # Create SAML assertion
        assertion = SAMLAssertion(
            assertion_id=assertion_id,
            session_id=assertion_id,
            user_email=user.email,
            user_name=user.display_name,
            roles=user.roles.get(target_cloud.value, []),
            issuer=provider.provider_id,
            audience=target_cloud.value,
            subject=user.user_id,
            conditions={
                "not_before": datetime.utcnow(),
                "not_on_or_after": datetime.utcnow() + timedelta(minutes=self.session_timeout)
            },
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=self.session_timeout)
        )
        
        # Store assertion
        self.saml_assertions[assertion_id] = assertion
        
        logger.info(f"SAML assertion created: {assertion_id}")
        return assertion
    
    def validate_saml_assertion(
        self,
        assertion_id: str
    ) -> Optional[SAMLAssertion]:
        """
        Validate SAML assertion
        
        Args:
            assertion_id: Assertion ID
            
        Returns:
            SAML assertion if valid, None otherwise
        """
        assertion = self.saml_assertions.get(assertion_id)
        
        if not assertion:
            logger.warning(f"SAML assertion not found: {assertion_id}")
            return None
        
        # Check expiration
        if assertion.expires_at < datetime.utcnow():
            logger.warning(f"SAML assertion expired: {assertion_id}")
            return None
        
        return assertion
    
    def create_sso_session(
        self,
        user: UserIdentity,
        provider: IdentityProvider,
        ip_address: str,
        user_agent: str
    ) -> SSOSession:
        """
        Create SSO session
        
        Args:
            user: User identity
            provider: Identity provider
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            SSO session
        """
        logger.info(f"Creating SSO session for user {user.user_id}")
        
        # Generate session ID
        session_id = f"session-{secrets.token_urlsafe(32)}"
        
        # Create session
        session = SSOSession(
            session_id=session_id,
            user_id=user.user_id,
            provider_id=provider.provider_id,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=self.session_timeout),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store session
        self.sessions[session_id] = session
        
        logger.info(f"SSO session created: {session_id}")
        return session
    
    def validate_session(
        self,
        session_id: str
    ) -> Optional[SSOSession]:
        """
        Validate SSO session
        
        Args:
            session_id: Session ID
            
        Returns:
            SSO session if valid, None otherwise
        """
        session = self.sessions.get(session_id)
        
        if not session:
            logger.warning(f"SSO session not found: {session_id}")
            return None
        
        # Check if session is valid
        if not session.is_valid:
            logger.warning(f"SSO session is invalid: {session_id}")
            return None
        
        # Check expiration
        if session.expires_at < datetime.utcnow():
            logger.warning(f"SSO session expired: {session_id}")
            session.is_valid = False
            return None
        
        return session
    
    def refresh_session(
        self,
        session_id: str
    ) -> Optional[SSOSession]:
        """
        Refresh SSO session
        
        Args:
            session_id: Session ID
            
        Returns:
            Refreshed SSO session if successful, None otherwise
        """
        session = self.validate_session(session_id)
        if not session:
            return None
        
        # Extend session expiration
        session.expires_at = datetime.utcnow() + timedelta(minutes=self.session_timeout)
        
        logger.info(f"SSO session refreshed: {session_id}")
        return session
    
    def revoke_session(
        self,
        session_id: str
    ) -> bool:
        """
        Revoke SSO session
        
        Args:
            session_id: Session ID
            
        Returns:
            True if session was revoked, False otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Mark session as invalid
        session.is_valid = False
        
        logger.info(f"SSO session revoked: {session_id}")
        return True
    
    def generate_saml_response(
        self,
        assertion: SAMLAssertion,
        private_key: rsa.RSAPrivateKey,
        certificate: x509.Certificate
    ) -> str:
        """
        Generate SAML response
        
        Args:
            assertion: SAML assertion
            private_key: Private key for signing
            certificate: Certificate for encryption
            
        Returns:
            SAML response XML
        """
        # In real implementation, generate proper SAML XML response
        # This is a simplified version
        
        saml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                ID="{assertion.assertion_id}"
                Version="2.0"
                IssueInstant="{assertion.issued_at.isoformat()}Z"
                Destination="{assertion.audience}"
                Consent="urn:oasis:names:tc:SAML:2.0:consent:unspecified">
    <saml:Issuer>{assertion.issuer}</saml:Issuer>
    <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
    </samlp:Status>
    <saml:Assertion ID="{assertion.assertion_id}"
                   Version="2.0"
                   IssueInstant="{assertion.issued_at.isoformat()}Z">
        <saml:Issuer>{assertion.issuer}</saml:Issuer>
        <saml:Subject>
            <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
                {assertion.user_email}
            </saml:NameID>
            <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <saml:SubjectConfirmationData NotOnOrAfter="{assertion.expires_at.isoformat()}Z"
                                               Recipient="{assertion.audience}"/>
            </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:Conditions NotBefore="{assertion.conditions['not_before'].isoformat()}Z"
                         NotOnOrAfter="{assertion.conditions['not_on_or_after'].isoformat()}Z">
            <saml:AudienceRestriction>
                <saml:Audience>{assertion.audience}</saml:Audience>
            </saml:AudienceRestriction>
        </saml:Conditions>
        <saml:AttributeStatement>
            <saml:Attribute Name="Roles">
                <saml:AttributeValue>{','.join(assertion.roles)}</saml:AttributeValue>
            </saml:Attribute>
        </saml:AttributeStatement>
    </saml:Assertion>
</samlp:Response>"""
        
        return saml_response
    
    def get_sso_url(
        self,
        provider: IdentityProvider,
        redirect_uri: str,
        state: Optional[str] = None
    ) -> str:
        """
        Get SSO login URL
        
        Args:
            provider: Identity provider
            redirect_uri: Redirect URI after authentication
            state: State parameter for CSRF protection
            
        Returns:
            SSO login URL
        """
        # Generate state if not provided
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Build SSO URL based on provider
        if provider.cloud == CloudProvider.AZURE:
            base_url = f"https://login.microsoftonline.com/{provider.tenant_id}/saml2"
        elif provider.cloud == CloudProvider.AWS:
            base_url = "https://signin.aws.amazon.com/saml"
        else:
            raise ValueError(f"Unsupported cloud: {provider.cloud}")
        
        # Add query parameters
        params = {
            "SAMLRequest": self._encode_saml_request(provider),
            "RelayState": redirect_uri,
            "state": state
        }
        
        sso_url = f"{base_url}?{urlencode(params)}"
        
        return sso_url
    
    def _encode_saml_request(
        self,
        provider: IdentityProvider
    ) -> str:
        """
        Encode SAML authentication request
        
        Args:
            provider: Identity provider
            
        Returns:
            Base64-encoded SAML request
        """
        # In real implementation, generate proper SAML request
        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                    ID="request-{secrets.token_urlsafe(16)}"
                    Version="2.0"
                    IssueInstant="{datetime.utcnow().isoformat()}Z"
                    Destination="https://login.microsoftonline.com/{provider.tenant_id}/saml2"
                    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
        {provider.client_id}
    </saml:Issuer>
</samlp:AuthnRequest>"""
        
        # Base64 encode
        encoded = base64.b64encode(saml_request.encode()).decode()
        
        return encoded
    
    async def handle_saml_response(
        self,
        saml_response: str,
        state: str
    ) -> Optional[Tuple[UserIdentity, SSOSession]]:
        """
        Handle SAML response from identity provider
        
        Args:
            saml_response: Base64-encoded SAML response
            state: State parameter
            
        Returns:
            Tuple of (user identity, SSO session) if successful, None otherwise
        """
        try:
            # Decode SAML response
            saml_xml = base64.b64decode(saml_response).decode()
            
            # Parse SAML assertion
            assertion = self._parse_saml_assertion(saml_xml)
            
            if not assertion:
                logger.error("Failed to parse SAML assertion")
                return None
            
            # Validate assertion
            validated_assertion = self.validate_saml_assertion(assertion.assertion_id)
            if not validated_assertion:
                logger.error("SAML assertion validation failed")
                return None
            
            # Get user identity
            user = await self._get_user_from_assertion(validated_assertion)
            if not user:
                logger.error("Failed to get user from assertion")
                return None
            
            # Create SSO session
            session = self.create_sso_session(
                user=user,
                provider=IdentityProvider(
                    provider_id=assertion.issuer,
                    name=assertion.issuer,
                    cloud=CloudProvider.AZURE if "azure" in assertion.issuer.lower() else CloudProvider.AWS,
                    tenant_id="",
                    client_id="",
                    client_secret=""
                ),
                ip_address="",
                user_agent=""
            )
            
            logger.info(f"SAML response handled successfully for user: {user.user_id}")
            return (user, session)
            
        except Exception as e:
            logger.error(f"Failed to handle SAML response: {e}")
            return None
    
    def _parse_saml_assertion(
        self,
        saml_xml: str
    ) -> Optional[SAMLAssertion]:
        """
        Parse SAML assertion from XML
        
        Args:
            saml_xml: SAML XML string
            
        Returns:
            SAML assertion if parsed successfully, None otherwise
        """
        try:
            # In real implementation, use xml.etree.ElementTree or lxml
            # This is a simplified version
            
            # Extract key information from XML
            # For now, return None (would need proper XML parsing)
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse SAML assertion: {e}")
            return None
    
    async def _get_user_from_assertion(
        self,
        assertion: SAMLAssertion
    ) -> Optional[UserIdentity]:
        """
        Get user identity from SAML assertion
        
        Args:
            assertion: SAML assertion
            
        Returns:
            User identity if found, None otherwise
        """
        # In real implementation, look up or create user
        # For now, return mock user
        from .identity_federation import CloudProvider
        
        return UserIdentity(
            user_id=f"sso-{assertion.user_email}",
            email=assertion.user_email,
            display_name=assertion.user_name,
            primary_cloud=CloudProvider.AZURE,
            created_at=datetime.utcnow()
        )
    
    def get_active_sessions(
        self,
        user_id: Optional[str] = None
    ) -> List[SSOSession]:
        """
        Get active SSO sessions
        
        Args:
            user_id: User ID (optional, all sessions if not specified)
            
        Returns:
            List of active sessions
        """
        active_sessions = []
        
        for session in self.sessions.values():
            # Check if session is valid and not expired
            if session.is_valid and session.expires_at > datetime.utcnow():
                # Filter by user if specified
                if user_id is None or session.user_id == user_id:
                    active_sessions.append(session)
        
        return active_sessions
    
    async def get_sso_analytics(self) -> Dict:
        """
        Get SSO analytics
        
        Returns:
            SSO statistics
        """
        active_sessions = self.get_active_sessions()
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active_sessions),
            "total_assertions": len(self.saml_assertions),
            "sessions_by_provider": self._count_by_provider(active_sessions)
        }
    
    def _count_by_provider(
        self,
        sessions: List[SSOSession]
    ) -> Dict[str, int]:
        """Count sessions by provider"""
        counts = {}
        for session in sessions:
            provider_id = session.provider_id
            counts[provider_id] = counts.get(provider_id, 0) + 1
        return counts