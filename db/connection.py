"""
Database connection — single place for all DB access.
Uses psycopg2 with a simple connection pool.
"""

import os
from urllib.parse import urlparse, parse_qs

import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

_pool: pool.SimpleConnectionPool | None = None


def _parse_db_url(url: str) -> dict:
    """
    Parse a postgres URL into psycopg2 keyword args.
    This avoids DSN-string parsing issues with libpq versions that don't
    recognize newer params like `channel_binding`. Only known-safe params
    are forwarded to psycopg2.
    """
    p = urlparse(url)
    kwargs = {
        "host":     p.hostname,
        "port":     p.port or 5432,
        "user":     p.username,
        "password": p.password,
        "dbname":   (p.path or "/").lstrip("/"),
    }
    # Forward query params that psycopg2 / libpq understand widely.
    safe_params = {"sslmode", "connect_timeout", "application_name"}
    for k, v in parse_qs(p.query).items():
        if k in safe_params and v:
            kwargs[k] = v[0]
    # Default to TLS for cloud Postgres (Neon, Supabase, etc.)
    if "sslmode" not in kwargs and p.hostname and "neon.tech" in p.hostname:
        kwargs["sslmode"] = "require"
    return kwargs


def _get_pool() -> pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        url = os.environ["DATABASE_URL"].strip()
        kwargs = _parse_db_url(url)
        _pool = pool.SimpleConnectionPool(minconn=1, maxconn=5, **kwargs)
    return _pool


@contextmanager
def get_conn():
    """Context manager — borrows a connection, commits on success, rolls back on error."""
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def init_schema():
    """Run schema.sql against the database (idempotent — safe to re-run)."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        sql = f.read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("Schema initialised.")
