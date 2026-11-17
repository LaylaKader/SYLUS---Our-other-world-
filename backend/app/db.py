from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from .config import settings


def _check_connection(conn):
    """Discard pooled connections that the hosted database has already closed."""
    conn.execute("SELECT 1")


# Neon may suspend idle compute and close existing SSL connections. Validate
# every checked-out connection and avoid holding an always-open idle connection.
pool = ConnectionPool(
    settings.database_url,
    min_size=0,
    max_size=5,
    max_idle=120,
    max_lifetime=1800,
    timeout=20,
    reconnect_timeout=30,
    check=_check_connection,
    open=False,
)


def open_pool():
    pool.open()
    pool.wait()


@contextmanager
def connection():
    with pool.connection() as conn:
        yield conn
