"""Prometheus metrics for monitoring application performance and health."""
import time

from fastapi import Request, Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)
from starlette.middleware.base import BaseHTTPMiddleware

# HTTP Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Database Connection Metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    ['database_type']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['database_type', 'query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

db_query_errors_total = Counter(
    'db_query_errors_total',
    'Total number of database query errors',
    ['database_type', 'error_type']
)

# Query Service Metrics
query_requests_total = Counter(
    'query_requests_total',
    'Total number of query requests',
    ['status']
)

query_duration_seconds = Histogram(
    'query_duration_seconds',
    'Query execution duration in seconds',
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

gemini_api_calls_total = Counter(
    'gemini_api_calls_total',
    'Total number of Gemini API calls',
    ['status']
)

gemini_api_duration_seconds = Histogram(
    'gemini_api_duration_seconds',
    'Gemini API call duration in seconds',
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

# Rate Limiting Metrics
rate_limit_hits_total = Counter(
    'rate_limit_hits_total',
    'Total number of rate limit hits',
    ['endpoint']
)

# Active Users/Projects
active_projects = Gauge(
    'active_projects',
    'Number of active projects'
)

active_accounts = Gauge(
    'active_accounts',
    'Number of active accounts'
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Get endpoint path (simplified, remove query params and IDs)
        endpoint = self._normalize_path(request.url.path)

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Record metrics
            duration = time.time() - start_time
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)

            return response
        except Exception:
            # Record error
            duration = time.time() - start_time
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
            raise

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing IDs with placeholders."""
        # Replace UUIDs and numeric IDs with placeholders
        import re
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        path = re.sub(r'/\d+', '/{id}', path)
        return path


def get_metrics_response() -> Response:
    """Get Prometheus metrics in text format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
