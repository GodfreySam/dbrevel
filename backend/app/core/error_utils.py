"""Centralized error handling utilities for safe error logging and reporting."""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Patterns that might indicate sensitive data
SENSITIVE_PATTERNS = [
    r"password\s*[:=]\s*['\"]?([^'\"]+)['\"]?",
    r"api[_-]?key\s*[:=]\s*['\"]?([^'\"]+)['\"]?",
    r"secret\s*[:=]\s*['\"]?([^'\"]+)['\"]?",
    r"token\s*[:=]\s*['\"]?([^'\"]+)['\"]?",
    r"authorization\s*[:=]\s*['\"]?([^'\"]+)['\"]?",
    r"x-project-key\s*[:=]\s*['\"]?([^'\"]+)['\"]?",
    r"postgresql://[^:]+:([^@]+)@",  # Database password in URL
    r"mongodb://[^:]+:([^@]+)@",  # Database password in URL
]


def sanitize_error_message(message: str) -> str:
    """
    Sanitize error message to remove potentially sensitive data.

    Args:
        message: The error message to sanitize

    Returns:
        Sanitized error message with sensitive data masked
    """
    sanitized = message

    # Mask sensitive patterns
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(
            pattern,
            lambda m: (
                m.group(0).replace(m.group(1), "***REDACTED***")
                if m.lastindex
                else m.group(0)
            ),
            sanitized,
            flags=re.IGNORECASE,
        )

    return sanitized


def truncate_error_message(error: Exception, max_length: int = 200) -> str:
    """
    Truncate long error messages to keep logs clean and prevent information leakage.

    Also sanitizes sensitive data from error messages.

    Args:
        error: The exception to format
        max_length: Maximum length of the error message

    Returns:
        Truncated and sanitized error message
    """
    error_str = str(error)

    # Sanitize sensitive data first
    error_str = sanitize_error_message(error_str)

    # Remove verbose topology descriptions from MongoDB errors
    if "Topology Description" in error_str:
        parts = error_str.split("Topology Description")
        if parts:
            error_str = parts[0].strip()

    # Remove verbose DNS resolution details
    if (
        "DNS operation timed out" in error_str
        or "resolution lifetime expired" in error_str
    ):
        if ":" in error_str:
            error_str = error_str.split(":")[0] + ": DNS resolution timeout"

    # Truncate if still too long
    if len(error_str) > max_length:
        error_str = error_str[:max_length] + "..."

    return error_str


def safe_log_error(
    logger_instance: logging.Logger,
    message: str,
    exc_info: bool = False,
    extra: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None:
    """
    Safely log an error message, ensuring no sensitive data is exposed.

    Args:
        logger_instance: The logger instance to use
        message: The error message (will be sanitized)
        exc_info: Whether to include exception info
        extra: Additional context to log
        **kwargs: Additional keyword arguments for logging
    """
    sanitized_message = sanitize_error_message(message)

    # Sanitize extra context if provided
    sanitized_extra = None
    if extra:
        sanitized_extra = {}
        for key, value in extra.items():
            if isinstance(value, str):
                sanitized_extra[key] = sanitize_error_message(value)
            else:
                sanitized_extra[key] = value

    logger_instance.error(
        sanitized_message, exc_info=exc_info, extra=sanitized_extra, **kwargs
    )


def safe_log_warning(logger_instance: logging.Logger, message: str, **kwargs) -> None:
    """
    Safely log a warning message, ensuring no sensitive data is exposed.

    Args:
        logger_instance: The logger instance to use
        message: The warning message (will be sanitized)
        **kwargs: Additional keyword arguments for logging
    """
    sanitized_message = sanitize_error_message(message)
    logger_instance.warning(sanitized_message, **kwargs)
