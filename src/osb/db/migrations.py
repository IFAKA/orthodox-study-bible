"""Version-gated schema migrations."""

import sqlite3

from osb.db.schema import SCHEMA_VERSION


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply any pending migrations based on schema_version in meta."""
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    current = int(row["value"]) if row else 0

    # Future migrations go here, e.g.:
    # if current < 2:
    #     conn.executescript("ALTER TABLE ...")
    #     conn.execute("UPDATE meta SET value='2' WHERE key='schema_version'")
    #     conn.commit()
    #     current = 2

    if current < SCHEMA_VERSION:
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
