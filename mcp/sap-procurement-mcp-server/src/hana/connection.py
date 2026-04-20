"""HANA Cloud connection module.

Provides a shared, auto-reconnecting HANA connection for all MCP tools.
Reuses the hdbcli pattern from Lab 52 (sap-procurement-rag).
"""
import os
import logging
from contextlib import contextmanager
from hdbcli import dbapi

logger = logging.getLogger(__name__)

# Module-level singleton connection
_connection = None


def _create_connection():
    """Create a new HANA connection using environment variables."""
    address = os.getenv("HANA_ADDRESS")
    port = int(os.getenv("HANA_PORT", "443"))
    user = os.getenv("HANA_USER")
    password = os.getenv("HANA_PASSWORD")

    if not all([address, user, password]):
        raise RuntimeError(
            "Missing HANA credentials. Set HANA_ADDRESS, HANA_USER, HANA_PASSWORD in .env"
        )

    logger.info("[HANA] Connecting to %s:%s as %s", address, port, user)
    conn = dbapi.connect(
        address=address,
        port=port,
        user=user,
        password=password,
        encrypt=True,
        sslValidateCertificate=False,
    )
    logger.info("[HANA] Connected successfully")
    return conn


def get_connection():
    """Return the shared HANA connection, creating/reconnecting if needed."""
    global _connection
    if _connection is None or not _connection.isconnected():
        _connection = _create_connection()
    return _connection


@contextmanager
def get_cursor():
    """Yield a cursor on the shared connection; close it on exit.

    Usage:
        with get_cursor() as cursor:
            cursor.execute("SELECT 1 FROM DUMMY")
            row = cursor.fetchone()
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def close_connection():
    """Close the shared connection (call on graceful shutdown)."""
    global _connection
    if _connection is not None and _connection.isconnected():
        _connection.close()
        _connection = None
        logger.info("[HANA] Connection closed")
