"""Account API key generation and validation utilities."""

import secrets
import hashlib


def generate_account_key(prefix: str = "dbrevel") -> str:
    """
    Generate a secure, URL-safe account API key.

    Format: {prefix}_{random_token}
    Example: dbrevel_abc123def456...

    Args:
        prefix: Optional prefix for the key (default: "dbrevel")

    Returns:
        A secure random API key string
    """
    # Convert to URL-safe base64-like string (using hex for readability)
    token = secrets.token_urlsafe(32)

    return f"{prefix}_{token}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Uses SHA-256 for one-way hashing. Store the hash, not the raw key.

    Args:
        api_key: The raw API key to hash

    Returns:
        SHA-256 hash of the key (hex string)
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against a stored hash.

    Args:
        api_key: The API key to verify
        stored_hash: The stored hash to compare against

    Returns:
        True if the key matches the hash, False otherwise
    """
    computed_hash = hash_api_key(api_key)
    return secrets.compare_digest(computed_hash, stored_hash)


def generate_readable_key(prefix: str = "dbrevel", length: int = 24) -> str:
    """
    Generate a more readable API key (for display purposes).

    Format: {prefix}_{readable_token}
    Example: dbrevel_abc123def456ghi789

    Args:
        prefix: Optional prefix for the key
        length: Length of the token part (default: 24)

    Returns:
        A readable API key string
    """
    # Use alphanumeric characters (excluding confusing chars like 0, O, I, l)
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    token = ''.join(secrets.choice(alphabet) for _ in range(length))

    return f"{prefix}_{token}"
