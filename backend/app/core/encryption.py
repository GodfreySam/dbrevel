"""Encryption utilities for sensitive data like database connection strings."""

from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, key: str = None):
        """
        Initialize encryption service.

        Args:
            key: Encryption key (32-byte base64-encoded). If None, uses ENCRYPTION_KEY or SECRET_KEY from settings.
        """
        if key is None:
            # Try ENCRYPTION_KEY first, fall back to SECRET_KEY
            encryption_key = getattr(settings, "ENCRYPTION_KEY", None)
            if (
                encryption_key
                and encryption_key != "your-encryption-key-here-generate-a-32-byte-key"
            ):
                key = encryption_key
            else:
                # Derive a 32-byte key from SECRET_KEY using SHA256
                key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
                key = base64.urlsafe_b64encode(key_bytes).decode()

        # Ensure key is properly formatted
        if len(key) != 44:  # Fernet keys are 44 characters (base64-encoded 32 bytes)
            # If key is not the right length, derive it
            key_bytes = hashlib.sha256(key.encode()).digest()
            key = base64.urlsafe_b64encode(key_bytes).decode()

        self.cipher = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string.

        Args:
            ciphertext: Encrypted string to decrypt

        Returns:
            Decrypted plaintext string

        Raises:
            Exception: If decryption fails (invalid key or corrupted data)
        """
        if not ciphertext:
            return ""

        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            # If decryption fails, try to handle legacy unencrypted data
            # In production, you might want to log this and handle it differently
            raise ValueError(f"Failed to decrypt data: {str(e)}")

    def mask_url(self, url: str) -> str:
        """
        Mask a connection URL for display (hides sensitive parts).

        Args:
            url: Database connection URL

        Returns:
            Masked URL with password and sensitive parts hidden
        """
        if not url:
            return ""

        try:
            # Parse URL and mask password
            if url.startswith("postgresql://") or url.startswith("postgres://"):
                # Format: postgresql://user:password@host:port/database
                parts = url.split("@")
                if len(parts) == 2:
                    auth_part = parts[0]
                    rest = parts[1]
                    if ":" in auth_part:
                        user = auth_part.split("://")[1].split(":")[0]
                        protocol = auth_part.split("://")[0]
                        return f"{protocol}://{user}:***@{rest}"
                return url.replace("://", "://***@").split("@")[0] + "@***"

            elif url.startswith("mongodb://") or url.startswith("mongodb+srv://"):
                # Format: mongodb://user:password@host:port/database
                parts = url.split("@")
                if len(parts) == 2:
                    auth_part = parts[0]
                    rest = parts[1]
                    if "://" in auth_part and ":" in auth_part:
                        protocol = auth_part.split("://")[0]
                        user = auth_part.split("://")[1].split(":")[0]
                        return f"{protocol}://{user}:***@{rest}"
                return url.replace("://", "://***@").split("@")[0] + "@***"

            return url
        except Exception:
            # If parsing fails, return a generic masked version
            if "@" in url:
                return url.split("@")[0].split("://")[0] + "://***@***"
            return "***"


# Global encryption service instance
_encryption_service: EncryptionService = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_database_url(url: str) -> str:
    """
    Encrypt a database connection URL.

    Args:
        url: Plaintext database URL

    Returns:
        Encrypted URL string
    """
    if not url:
        return ""
    return get_encryption_service().encrypt(url)


def decrypt_database_url(encrypted_url: str) -> str:
    """
    Decrypt a database connection URL.

    Args:
        encrypted_url: Encrypted database URL

    Returns:
        Decrypted plaintext URL

    Raises:
        ValueError: If decryption fails
    """
    if not encrypted_url:
        return ""

    # Strip whitespace for robustness
    encrypted_url = encrypted_url.strip()

    # Check if already decrypted (for backward compatibility with existing data)
    if encrypted_url.startswith(
        ("postgresql://", "postgres://", "mongodb://", "mongodb+srv://")
    ):
        return encrypted_url

    return get_encryption_service().decrypt(encrypted_url)


def mask_database_url(url: str) -> str:
    """
    Mask a database URL for safe display (hides passwords).

    Args:
        url: Database URL (encrypted or plaintext)

    Returns:
        Masked URL string safe for display
    """
    if not url:
        return ""

    # If encrypted, we can't mask it directly, so return a generic message
    if not url.startswith(
        ("postgresql://", "postgres://", "mongodb://", "mongodb+srv://")
    ):
        return "*** (encrypted)"

    return get_encryption_service().mask_url(url)
