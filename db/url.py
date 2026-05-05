"""
Database URL
============

Build database connection URL from environment variables.
"""

from os import getenv
from urllib.parse import quote


def build_db_url() -> str:
    """Build database URL from environment variables.

    Includes SQLAlchemy connection pool parameters so that multiple API
    replicas (each with multiple uvicorn workers) don't exhaust the
    PostgreSQL max_connections limit.

    Pool sizing rationale:
      pool_size=5       — connections kept open per process (5 workers × N replicas)
      max_overflow=10   — burst headroom per process
      pool_timeout=30   — seconds to wait for a connection before raising
      pool_pre_ping=true — discard stale connections after DB restart/failover

    SSL:
      DB_SSL_REQUIRED=true  — required when connecting to Azure Database for
                              PostgreSQL Flexible Server (enforced by default).
                              Set automatically by deploy.ps1 when useManagedPostgres=true.
    """
    driver = getenv("DB_DRIVER", "postgresql+psycopg")
    user = getenv("DB_USER", "ai")
    password = quote(getenv("DB_PASS", "ai"), safe="")
    host = getenv("DB_HOST", "localhost")
    port = getenv("DB_PORT", "5432")
    database = getenv("DB_DATABASE", "ai")

    base = f"{driver}://{user}:{password}@{host}:{port}/{database}"

    # Allow overriding pool params via env for tuning without code changes
    pool_size    = getenv("DB_POOL_SIZE",    "5")
    max_overflow = getenv("DB_MAX_OVERFLOW", "10")
    pool_timeout = getenv("DB_POOL_TIMEOUT", "30")

    params = (
        f"?pool_size={pool_size}"
        f"&max_overflow={max_overflow}"
        f"&pool_timeout={pool_timeout}"
        f"&pool_pre_ping=true"
    )

    # Azure Database for PostgreSQL Flexible Server requires SSL by default
    if getenv("DB_SSL_REQUIRED", "false").lower() == "true":
        params += "&sslmode=require"

    return base + params


db_url = build_db_url()
