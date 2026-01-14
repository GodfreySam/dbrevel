"""Lightweight per-tenant usage logging with MongoDB persistence."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional


def record_usage(
    account_id: str,
    trace_id: str,
    execution_time_ms: float,
    gemini_tokens_used: int = 0,
) -> None:
    """
    Record usage for a tenant (sync version for backward compatibility).

    For v1 this just logs to stdout; later this can be wired to a database table
    or an external analytics/billing system.
    """

    # Keep parameter name for backward compatibility but prefer `account_id` terminology
    timestamp = datetime.utcnow().isoformat()
    print(
        f"[USAGE] ts={timestamp} account={account_id} trace={trace_id} "
        f"exec_ms={execution_time_ms:.2f} gemini_tokens={gemini_tokens_used}"
    )


async def record_usage_async(
    account_id: str,
    project_id: Optional[str],
    trace_id: str,
    execution_time_ms: float,
    query_type: str,
    gemini_tokens_used: int = 0,
    status: str = "success",
    error_message: Optional[str] = None,
) -> None:
    """
    Record usage to MongoDB for analytics.

    Also logs to stdout for backward compatibility.

    Args:
        account_id: Account ID
        project_id: Project ID (optional, for multi-project setups)
        trace_id: Unique trace ID for the query
        execution_time_ms: Query execution time in milliseconds
        query_type: Type of query ("postgres" or "mongodb")
        gemini_tokens_used: Number of Gemini tokens consumed
        status: Query status ("success" or "error")
        error_message: Error message if status is "error"
    """
    # Stdout logging (backward compatibility)
    timestamp = datetime.utcnow()
    print(
        f"[USAGE] ts={timestamp.isoformat()} account={account_id} "
        f"project={project_id or 'N/A'} trace={trace_id} "
        f"exec_ms={execution_time_ms:.2f} tokens={gemini_tokens_used} "
        f"type={query_type} status={status}"
    )

    # MongoDB persistence
    from app.core.account_store import get_account_store

    tenant_store = get_account_store()
    # Only persist if using MongoDB account store (production)
    if tenant_store and hasattr(tenant_store, "db") and tenant_store.db:
        try:
            log_id = f"log_{uuid.uuid4().hex}"

            await tenant_store.db.usage_logs.insert_one(
                {
                    "log_id": log_id,
                    "account_id": account_id,
                    "project_id": project_id,
                    "trace_id": trace_id,
                    "execution_time_ms": execution_time_ms,
                    "query_type": query_type,
                    "gemini_tokens_used": gemini_tokens_used,
                    "timestamp": timestamp,
                    "status": status,
                    "error_message": error_message,
                }
            )
        except Exception as e:
            # Don't fail the request if logging fails
            print(f"[USAGE] Failed to persist usage log: {e}")
