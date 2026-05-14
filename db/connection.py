"""
Database connection — single place for all DB access.
Uses psycopg2 with a simple connection pool.
"""

import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

_pool: pool.SimpleConnectionPool | None = None


def _clean_dsn(dsn: str) -> str:
    """
    Strip Neon-specific URL params that older libpq versions reject.
    `channel_binding` requires libpq 13+; GitHub Actions Ubuntu may ship older.
    SSL is still enforced via `sslmode=require`.
    """
    for bad in ("&channel_binding=require", "?channel_binding=require"):
        dsn = dsn.replace(bad, "")
    return dsn


def _get_pool() -> pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        dsn = _clean_dsn(os.environ["DATABASE_URL"])
        _pool = pool.SimpleConnectionPool(minconn=1, maxconn=5, dsn=dsn)
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
