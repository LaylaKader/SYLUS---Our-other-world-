from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from .config import settings

pool = ConnectionPool(settings.database_url, min_size=1, max_size=5, open=False)

def open_pool():
    pool.open()
    pool.wait()

@contextmanager
def connection():
    with pool.connection() as conn:
        yield conn
