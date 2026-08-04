"""
Encryption at Rest Service
Enterprise-grade data encryption for storage
"""

from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    key_type: str  # symmetric, asymmetric
    algorithm: str  # AES-256, RSA-2048, etc.
    version: int
    created_at: datetime
    expires_at: Optional[datetime]
    status: str  # active, rotated, revoked
    metadata: Dict[str, Any]


@dataclass
class EncryptedData:
    """Encrypted data container"""
    ciphertext: bytes
    key_id: str
    algorithm: str
    iv: bytes
    tag: bytes  # For authenticated encryption
    metadata: Dict[str, Any]


class EncryptionAtRest:
    """
    Enterprise encryption at rest service
    Supports AES-256-GCM, envelope encryption
    """

    def __init__(self, key_management_service):
        self.kms = key_management_service
        self.default_algorithm = "AES-256-GCM"
        self.encryption_cache: Dict[str, EncryptedData] = {}

    async def encrypt(
        self,
        plaintext: bytes,
        key_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> EncryptedData:
        """
        Encrypt data at rest

        Args:
            plaintext: Data to encrypt
            key_id: Encryption key ID (uses default if not provided)
            metadata: Additional metadata

        Returns:
            Encrypted data container
        """
        # Get encryption key
        key_id = key_id or await self.kms.get_default_key()
        key = await self.kms.get_key(key_id)

        # Generate IV
        iv = os.urandom(12)  # 96-bit IV for GCM

        try:
            # Encrypt data (AES-256-GCM)
            ciphertext, tag = self._encrypt_aes_gcm(
                plaintext,
                key.key_material,
                iv
            )

            encrypted_data = EncryptedData(
                ciphertext=ciphertext,
                key_id=key_id,
                algorithm=self.default_algorithm,
                iv=iv,
                tag=tag,
                metadata=metadata or {}
            )

            # Cache for performance
            cache_key = f"{key_id}:{plaintext.hex()[:32]}"
            self.encryption_cache[cache_key] = encrypted_data

            logger.info(f"Data encrypted with key {key_id}")

            return encrypted_data

        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise

    async def decrypt(
        self,
        encrypted_data: EncryptedData
    ) -> bytes:
        """
        Decrypt data at rest

        Args:
            encrypted_data: Encrypted data container

        Returns:
            Decrypted plaintext
        """
        try:
            # Get encryption key
            key = await self.kms.get_key(encrypted_data.key_id)

            # Decrypt data
            plaintext = self._decrypt_aes_gcm(
                encrypted_data.ciphertext,
                key.key_material,
                encrypted_data.iv,
                encrypted_data.tag
            )

            logger.info(f"Data decrypted with key {encrypted_data.key_id}")

            return plaintext

        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise

    async def encrypt_file(
        self,
        file_path: str,
        key_id: Optional[str] = None
    ) -> Tuple[str, EncryptedData]:
        """
        Encrypt file at rest

        Args:
            file_path: Path to file
            key_id: Encryption key ID

        Returns:
            Tuple of encrypted file path and encryption metadata
        """
        # Read file
        with open(file_path, "rb") as f:
            plaintext = f.read()

        # Encrypt
        encrypted_data = await self.encrypt(plaintext, key_id)

        # Write encrypted file
        encrypted_path = f"{file_path}.enc"
        with open(encrypted_path, "wb") as f:
            # Write IV + tag + ciphertext
            f.write(encrypted_data.iv)
            f.write(encrypted_data.tag)
            f.write(encrypted_data.ciphertext)

        logger.info(f"File encrypted: {file_path}")

        return encrypted_path, encrypted_data

    async def decrypt_file(
        self,
        encrypted_file_path: str
    ) -> bytes:
        """
        Decrypt file at rest

        Args:
            encrypted_file_path: Path to encrypted file

        Returns:
            Decrypted file contents
        """
        # Read encrypted file
        with open(encrypted_file_path, "rb") as f:
            # Read IV (12 bytes)
            iv = f.read(12)

            # Read tag (16 bytes)
            tag = f.read(16)

            # Read ciphertext
            ciphertext = f.read()

        # Create encrypted data container
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            key_id="",  # Extract from metadata or filename
            algorithm=self.default_algorithm,
            iv=iv,
            tag=tag,
            metadata={}
        )

        # Decrypt
        return await self.decrypt(encrypted_data)

    def _encrypt_aes_gcm(
        self,
        plaintext: bytes,
        key: bytes,
        iv: bytes
    ) -> Tuple[bytes, bytes]:
        """
        AES-256-GCM encryption

        Args:
            plaintext: Data to encrypt
            key: Encryption key (32 bytes for AES-256)
            iv: Initialization vector (12 bytes)

        Returns:
            Tuple of (ciphertext, tag)
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Initialize AES-GCM
        aesgcm = AESGCM(key)

        # Encrypt
        ciphertext = aesgcm.encrypt(iv, plaintext, None)

        # Split ciphertext and tag
        # GCM appends tag to ciphertext
        tag = ciphertext[-16:]
        ciphertext = ciphertext[:-16]

        return ciphertext, tag

    def _decrypt_aes_gcm(
        self,
        ciphertext: bytes,
        key: bytes,
        iv: bytes,
        tag: bytes
    ) -> bytes:
        """
        AES-256-GCM decryption

        Args:
            ciphertext: Encrypted data
            key: Encryption key
            iv: Initialization vector
            tag: Authentication tag

        Returns:
            Decrypted plaintext
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Initialize AES-GCM
        aesgcm = AESGCM(key)

        # Combine ciphertext and tag
        encrypted_data = ciphertext + tag

        # Decrypt
        plaintext = aesgcm.decrypt(iv, encrypted_data, None)

        return plaintext

    async def rotate_key(
        self,
        old_key_id: str,
        new_key_id: str
    ) -> Dict[str, Any]:
        """
        Rotate encryption key
        Re-encrypt data with new key

        Args:
            old_key_id: Old key ID
            new_key_id: New key ID

        Returns:
            Rotation report
        """
        logger.info(f"Starting key rotation: {old_key_id} -> {new_key_id}")

        report = {
            "old_key_id": old_key_id,
            "new_key_id": new_key_id,
            "started_at": datetime.utcnow().isoformat(),
            "records_rotated": 0,
            "errors": []
        }

        # In production, scan all encrypted data and re-encrypt
        # This is a simplified example

        logger.info(f"Key rotation completed")

        return report

    async def get_encryption_status(self) -> Dict[str, Any]:
        """
        Get encryption status

        Returns:
            Encryption status report
        """
        return {
            "algorithm": self.default_algorithm,
            "cached_encryptions": len(self.encryption_cache),
            "kms_status": await self.kms.get_status()
        }


class EnvelopeEncryption:
    """
    Envelope encryption for large datasets
    Encrypts data with data key, encrypts data key with master key
    """

    def __init__(self, key_management_service):
        self.kms = key_management_service

    async def encrypt_with_envelope(
        self,
        plaintext: bytes
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt using envelope encryption

        Args:
            plaintext: Data to encrypt

        Returns:
            Tuple of (encrypted_data_key, encrypted_data)
        """
        # Generate data key
        data_key = os.urandom(32)  # AES-256

        # Get master key
        master_key_id = await self.kms.get_default_key()
        master_key = await self.kms.get_key(master_key_id)

        # Encrypt data with data key
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        iv = os.urandom(12)
        aesgcm = AESGCM(data_key)
        ciphertext = aesgcm.encrypt(iv, plaintext, None)
        tag = ciphertext[-16:]
        ciphertext = ciphertext[:-16]

        # Encrypt data key with master key
        encrypted_data_key = self._encrypt_key(data_key, master_key)

        return encrypted_data_key, ciphertext + tag + iv

    async def decrypt_with_envelope(
        self,
        encrypted_data_key: bytes,
        ciphertext: bytes
    ) -> bytes:
        """
        Decrypt using envelope encryption

        Args:
            encrypted_data_key: Encrypted data key
            ciphertext: Encrypted data

        Returns:
            Decrypted plaintext
        """
        # Get master key
        master_key_id = await self.kms.get_default_key()
        master_key = await self.kms.get_key(master_key_id)

        # Decrypt data key
        data_key = self._decrypt_key(encrypted_data_key, master_key)

        # Extract IV and tag
        iv = ciphertext[-12:]
        tag = ciphertext[-28:-12]
        ciphertext = ciphertext[:-28]

        # Decrypt data
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(data_key)
        plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)

        return plaintext

    def _encrypt_key(self, data_key: bytes, master_key: EncryptionKey) -> bytes:
        """Encrypt data key with master key"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        iv = os.urandom(12)
        aesgcm = AESGCM(master_key.key_material)
        encrypted = aesgcm.encrypt(iv, data_key, None)
        return iv + encrypted

    def _decrypt_key(self, encrypted_key: bytes, master_key: EncryptionKey) -> bytes:
        """Decrypt data key with master key"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        iv = encrypted_key[:12]
        ciphertext = encrypted_key[12:]
        aesgcm = AESGCM(master_key.key_material)
        return aesgcm.decrypt(iv, ciphertext, None)