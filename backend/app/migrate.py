"""Apply additive, idempotent SQL migrations before the API starts."""
from pathlib import Path
import psycopg

from .config import settings


def run_migrations() -> None:
    migration_dir = Path(__file__).resolve().parent.parent / "migrations"
    files = sorted(migration_dir.glob("[0-9][0-9][0-9]_*.sql"))
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        for migration in files:
            version = migration.name
            already_applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s", (version,)
            ).fetchone()
            if already_applied:
                continue
            sql = migration.read_text(encoding="utf-8")
            # SQL files contain multiple statements; prepare=False uses simple-query mode.
            conn.execute(sql, prepare=False)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
