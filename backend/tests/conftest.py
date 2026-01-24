"""
Pytest configuration and fixtures for backend tests.

This file sets up test environment variables before any imports,
ensuring that Settings() can be instantiated during test collection.

Pytest automatically loads conftest.py before importing test modules,
so environment variables set here will be available when app modules
are imported.
"""
import os

# Set test environment variables BEFORE any app imports
# This ensures Settings() can be instantiated during test collection
# Pytest loads conftest.py before test files, so these will be set
# before app.main imports app.core.config which instantiates Settings()
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key-for-ci-testing-only")
os.environ.setdefault("POSTGRES_URL", "postgresql://test:test@localhost:5432/testdb")
os.environ.setdefault("MONGODB_URL", "mongodb://test:test@localhost:27017/testdb")
# Encryption key must be at least 32 chars with good entropy
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-chars-long-abc123!!")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32-chars!!")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DEMO_ACCOUNT_ENABLED", "false")  # Disable demo account creation in tests

# Note: Do NOT import any app modules here, as that would trigger
# Settings() instantiation before env vars are guaranteed to be set.
# Test files can safely import app modules after conftest.py is loaded.
