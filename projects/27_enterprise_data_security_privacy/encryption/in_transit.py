"""
Encryption in Transit Service
TLS/SSL certificate management and secure communications
"""

from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import ssl
import socket
from enum import Enum

logger = logging.getLogger(__name__)


class TLSVersion(str, Enum):
    """TLS protocol versions"""
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"


class CipherSuite(str, Enum):
    """Strong cipher suites"""
    TLS_AES_256_GCM_SHA384 = "TLS_AES_256_GCM_SHA384"
    TLS_CHACHA20_POLY1305_SHA256 = "TLS_CHACHA20_POLY1305_SHA256"
    TLS_AES_128_GCM_SHA256 = "TLS_AES_128_GCM_SHA256"


@dataclass
class Certificate:
    """SSL/TLS certificate"""
    cert_id: str
    domain: str
    issuer: str
    subject: str
    serial_number: str
    not_valid_before: datetime
    not_valid_after: datetime
    certificate_pem: str
    private_key_pem: str
    chain: List[str]
    metadata: Dict[str, Any]


@dataclass
class TLSConfig:
    """TLS configuration"""
    min_version: TLSVersion
    max_version: TLSVersion
    cipher_suites: List[CipherSuite]
    require_client_cert: bool
    verify_mode: int
    check_hostname: bool


class EncryptionInTransit:
    """
    Enterprise encryption in transit service
    Manages TLS/SSL certificates and secure communications
    """

    def __init__(self):
        self.certificates: Dict[str, Certificate] = {}
        self.default_tls_config = TLSConfig(
            min_version=TLSVersion.TLS_1_2,
            max_version=TLSVersion.TLS_1_3,
            cipher_suites=[
                CipherSuite.TLS_AES_256_GCM_SHA384,
                CipherSuite.TLS_CHACHA20_POLY1305_SHA256,
                CipherSuite.TLS_AES_128_GCM_SHA256
            ],
            require_client_cert=False,
            verify_mode=ssl.CERT_REQUIRED,
            check_hostname=True
        )

    async def generate_self_signed_cert(
        self,
        domain: str,
        validity_days: int = 365
    ) -> Certificate:
        """
        Generate self-signed certificate

        Args:
            domain: Domain name
            validity_days: Certificate validity in days

        Returns:
            Generated certificate
        """
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Enterprise Security"),
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False
        ).sign(private_key, hashes.SHA256())

        # Serialize
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        certificate = Certificate(
            cert_id=f"cert-{domain}-{datetime.utcnow().timestamp()}",
            domain=domain,
            issuer="Enterprise Security (Self-Signed)",
            subject=subject.rfc4514_string(),
            serial_number=str(cert.serial_number),
            not_valid_before=cert.not_valid_before,
            not_valid_after=cert.not_valid_after,
            certificate_pem=cert_pem.decode(),
            private_key_pem=key_pem.decode(),
            chain=[],
            metadata={"self_signed": True}
        )

        self.certificates[certificate.cert_id] = certificate
        logger.info(f"Self-signed certificate generated for {domain}")

        return certificate

    async def create_ssl_context(
        self,
        cert_path: str,
        key_path: str,
        config: Optional[TLSConfig] = None
    ) -> ssl.SSLContext:
        """
        Create SSL context for server

        Args:
            cert_path: Path to certificate file
            key_path: Path to private key file
            config: TLS configuration

        Returns:
            SSL context
        """
        config = config or self.default_tls_config

        # Create context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(cert_path, key_path)

        # Set TLS version
        context.minimum_version = config.min_version.value
        context.maximum_version = config.max_version.value

        # Set cipher suites
        context.set_ciphers(":".join([cs.value for cs in config.cipher_suites]))

        # Verify mode
        context.verify_mode = config.verify_mode
        context.check_hostname = config.check_hostname

        logger.info(f"SSL context created")

        return context

    async def validate_certificate(
        self,
        cert_pem: str
    ) -> Dict[str, Any]:
        """
        Validate certificate

        Args:
            cert_pem: Certificate PEM string

        Returns:
            Validation result
        """
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        try:
            # Load certificate
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

            # Check validity
            now = datetime.utcnow()
            is_valid = cert.not_valid_before <= now <= cert.not_valid_after

            # Days until expiration
            days_until_expiry = (cert.not_valid_after - now).days

            result = {
                "valid": is_valid,
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "serial_number": str(cert.serial_number),
                "not_valid_before": cert.not_valid_before.isoformat(),
                "not_valid_after": cert.not_valid_after.isoformat(),
                "days_until_expiry": days_until_expiry,
                "expired": now > cert.not_valid_after
            }

            if not is_valid:
                result["reason"] = "Certificate expired" if result["expired"] else "Certificate not yet valid"

            return result

        except Exception as e:
            logger.error(f"Certificate validation failed: {str(e)}")
            return {
                "valid": False,
                "reason": str(e)
            }

    async def check_certificate_expiry(
        self,
        cert_id: str
    ) -> Dict[str, Any]:
        """
        Check certificate expiry

        Args:
            cert_id: Certificate identifier

        Returns:
            Expiry status
        """
        if cert_id not in self.certificates:
            raise ValueError("Certificate not found")

        cert = self.certificates[cert_id]
        now = datetime.utcnow()
        days_until_expiry = (cert.not_valid_after - now).days

        return {
            "cert_id": cert_id,
            "domain": cert.domain,
            "expires_at": cert.not_valid_after.isoformat(),
            "days_until_expiry": days_until_expiry,
            "expired": days_until_expiry < 0,
            "expiring_soon": 0 < days_until_expiry < 30
        }

    async def rotate_certificate(
        self,
        cert_id: str,
        validity_days: int = 365
    ) -> Certificate:
        """
        Rotate expiring certificate

        Args:
            cert_id: Certificate to rotate
            validity_days: New certificate validity

        Returns:
            New certificate
        """
        if cert_id not in self.certificates:
            raise ValueError("Certificate not found")

        old_cert = self.certificates[cert_id]

        # Generate new certificate
        new_cert = await self.generate_self_signed_cert(
            old_cert.domain,
            validity_days
        )

        logger.info(f"Certificate rotated: {cert_id} -> {new_cert.cert_id}")

        return new_cert

    def create_secure_client_context(self) -> ssl.SSLContext:
        """
        Create secure SSL context for client

        Returns:
            SSL context
        """
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        return context

    async def test_tls_connection(
        self,
        host: str,
        port: int = 443
    ) -> Dict[str, Any]:
        """
        Test TLS connection to server

        Args:
            host: Server hostname
            port: Server port

        Returns:
            Connection test result
        """
        context = self.create_secure_client_context()

        try:
            with socket.create_connection((host, port)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

                    return {
                        "connected": True,
                        "host": host,
                        "port": port,
                        "tls_version": version,
                        "cipher": cipher,
                        "certificate": cert
                    }

        except Exception as e:
            logger.error(f"TLS connection test failed: {str(e)}")
            return {
                "connected": False,
                "host": host,
                "port": port,
                "error": str(e)
            }

    async def get_tls_status(self) -> Dict[str, Any]:
        """
        Get TLS configuration status

        Returns:
            TLS status
        """
        return {
            "default_config": {
                "min_version": self.default_tls_config.min_version.value,
                "max_version": self.default_tls_config.max_version.value,
                "cipher_suites": [cs.value for cs in self.default_tls_config.cipher_suites],
                "verify_mode": self.default_tls_config.verify_mode
            },
            "total_certificates": len(self.certificates),
            "certificates": [
                {
                    "cert_id": cert.cert_id,
                    "domain": cert.domain,
                    "expires_at": cert.not_valid_after.isoformat()
                }
                for cert in self.certificates.values()
            ]
        }