"""
Enterprise Key Management Service
Centralized key lifecycle management
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import secrets
from enum import Enum

logger = logging.getLogger(__name__)


class KeyType(str, Enum):
    """Key types"""
    SYMMETRIC = "symmetric"
    ASYMMETRIC_RSA = "asymmetric_rsa"
    ASYMMETRIC_ECDSA = "asymmetric_ecdsa"
    HMAC = "hmac"


class KeyStatus(str, Enum):
    """Key lifecycle status"""
    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"
    DESTROYED = "destroyed"


@dataclass
class EncryptionKey:
    """Encryption key with metadata"""
    key_id: str
    key_type: KeyType
    algorithm: str
    version: int
    key_material: bytes
    created_at: datetime
    expires_at: Optional[datetime]
    last_rotated: Optional[datetime]
    status: KeyStatus
    metadata: Dict[str, Any]


class KeyManagementService:
    """
    Enterprise Key Management Service (KMS)
    Manages encryption key lifecycle
    """

    def __init__(self):
        self.keys: Dict[str, EncryptionKey] = {}
        self.key_versions: Dict[str, List[str]] = {}
        self.rotation_schedule: Dict[str, int] = {}  # key_id -> days
        self.default_key_id: Optional[str] = None

    async def create_key(
        self,
        key_type: KeyType,
        algorithm: str,
        expires_in_days: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> EncryptionKey:
        """
        Create new encryption key

        Args:
            key_type: Type of key
            algorithm: Encryption algorithm
            expires_in_days: Key expiration (None = no expiry)
            metadata: Additional metadata

        Returns:
            Created encryption key
        """
        # Generate key material
        key_material = self._generate_key_material(key_type)

        # Create key
        key_id = f"key-{datetime.utcnow().timestamp()}"
        now = datetime.utcnow()

        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)

        key = EncryptionKey(
            key_id=key_id,
            key_type=key_type,
            algorithm=algorithm,
            version=1,
            key_material=key_material,
            created_at=now,
            expires_at=expires_at,
            last_rotated=now,
            status=KeyStatus.ACTIVE,
            metadata=metadata or {}
        )

        self.keys[key_id] = key
        self.key_versions[key_id] = [key_id]

        # Set as default if first key
        if not self.default_key_id:
            self.default_key_id = key_id

        logger.info(f"Key created - {key_id}")

        return key

    async def get_key(self, key_id: str) -> EncryptionKey:
        """
        Get encryption key

        Args:
            key_id: Key identifier

        Returns:
            Encryption key
        """
        if key_id not in self.keys:
            raise ValueError(f"Key not found: {key_id}")

        key = self.keys[key_id]

        # Check expiration
        if key.expires_at and datetime.utcnow() > key.expires_at:
            logger.warning(f"Key expired: {key_id}")
            key.status = KeyStatus.REVOKED

        return key

    async def get_default_key(self) -> str:
        """
        Get default encryption key

        Returns:
            Default key ID
        """
        if not self.default_key_id:
            raise ValueError("No default key configured")

        return self.default_key_id

    async def set_default_key(self, key_id: str):
        """
        Set default encryption key

        Args:
            key_id: Key identifier
        """
        if key_id not in self.keys:
            raise ValueError("Key not found")

        self.default_key_id = key_id
        logger.info(f"Default key set to {key_id}")

    async def rotate_key(self, key_id: str) -> EncryptionKey:
        """
        Rotate encryption key

        Args:
            key_id: Key to rotate

        Returns:
            New key version
        """
        if key_id not in self.keys:
            raise ValueError("Key not found")

        old_key = self.keys[key_id]

        # Create new version
        new_key = EncryptionKey(
            key_id=f"key-{datetime.utcnow().timestamp()}",
            key_type=old_key.key_type,
            algorithm=old_key.algorithm,
            version=old_key.version + 1,
            key_material=self._generate_key_material(old_key.key_type),
            created_at=datetime.utcnow(),
            expires_at=old_key.expires_at,
            last_rotated=datetime.utcnow(),
            status=KeyStatus.ACTIVE,
            metadata=old_key.metadata.copy()
        )

        # Store new key
        self.keys[new_key.key_id] = new_key
        self.key_versions[key_id].append(new_key.key_id)

        # Update old key status
        old_key.status = KeyStatus.ROTATED

        logger.info(f"Key rotated: {key_id} -> {new_key.key_id}")

        return new_key

    async def revoke_key(self, key_id: str):
        """
        Revoke encryption key

        Args:
            key_id: Key to revoke
        """
        if key_id not in self.keys:
            raise ValueError("Key not found")

        self.keys[key_id].status = KeyStatus.REVOKED
        logger.info(f"Key revoked: {key_id}")

    async def destroy_key(self, key_id: str):
        """
        Securely destroy encryption key

        Args:
            key_id: Key to destroy
        """
        if key_id not in self.keys:
            raise ValueError("Key not found")

        # Securely overwrite key material
        key = self.keys[key_id]
        key.key_material = secrets.token_bytes(len(key.key_material))
        key.status = KeyStatus.DESTROYED

        # Remove from active keys
        del self.keys[key_id]

        logger.info(f"Key destroyed: {key_id}")

    async def list_keys(
        self,
        status: Optional[KeyStatus] = None
    ) -> List[EncryptionKey]:
        """
        List encryption keys

        Args:
            status: Filter by status

        Returns:
            List of keys
        """
        keys = list(self.keys.values())

        if status:
            keys = [k for k in keys if k.status == status]

        return keys

    async def get_key_versions(self, key_id: str) -> List[str]:
        """
        Get all versions of a key

        Args:
            key_id: Key identifier

        Returns:
            List of version key IDs
        """
        return self.key_versions.get(key_id, [])

    async def schedule_rotation(self, key_id: str, days: int):
        """
        Schedule automatic key rotation

        Args:
            key_id: Key identifier
            days: Rotation interval in days
        """
        if key_id not in self.keys:
            raise ValueError("Key not found")

        self.rotation_schedule[key_id] = days
        logger.info(f"Key rotation scheduled: {key_id} every {days} days")

    async def check_rotation_needed(self) -> List[str]:
        """
        Check which keys need rotation

        Returns:
            List of key IDs needing rotation
        """
        keys_to_rotate = []

        for key_id, days in self.rotation_schedule.items():
            if key_id in self.keys:
                key = self.keys[key_id]
                if key.last_rotated:
                    days_since_rotation = (datetime.utcnow() - key.last_rotated).days
                    if days_since_rotation >= days:
                        keys_to_rotate.append(key_id)

        return keys_to_rotate

    def _generate_key_material(self, key_type: KeyType) -> bytes:
        """
        Generate cryptographic key material

        Args:
            key_type: Type of key

        Returns:
            Key material bytes
        """
        if key_type == KeyType.SYMMETRIC:
            # AES-256 (32 bytes)
            return secrets.token_bytes(32)
        elif key_type == KeyType.HMAC:
            # HMAC-SHA256 (32 bytes)
            return secrets.token_bytes(32)
        elif key_type == KeyType.ASYMMETRIC_RSA:
            # RSA-2048 (256 bytes)
            return secrets.token_bytes(256)
        elif key_type == KeyType.ASYMMETRIC_ECDSA:
            # ECDSA P-256 (32 bytes)
            return secrets.token_bytes(32)
        else:
            raise ValueError(f"Unsupported key type: {key_type}")

    async def get_status(self) -> Dict[str, Any]:
        """
        Get KMS status

        Returns:
            KMS status report
        """
        return {
            "total_keys": len(self.keys),
            "active_keys": len([k for k in self.keys.values() if k.status == KeyStatus.ACTIVE]),
            "rotated_keys": len([k for k in self.keys.values() if k.status == KeyStatus.ROTATED]),
            "revoked_keys": len([k for k in self.keys.values() if k.status == KeyStatus.REVOKED]),
            "default_key": self.default_key_id,
            "keys_scheduled_for_rotation": len(await self.check_rotation_needed())
        }