"""Apply Postgres schema migrations in backend/migrations.

This is intentionally tiny: the app only needs ordered SQL files and a version
table, not a full migration framework.
"""
import os

from db import close_pool, get_conn

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")


def migration_files() -> list[str]:
    return sorted(
        name for name in os.listdir(MIGRATIONS_DIR)
        if name.endswith(".sql")
    )


def apply_migrations() -> list[str]:
    applied: list[str] = []
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        seen = {row["version"] for row in rows}

        for filename in migration_files():
            version = filename.split("_", 1)[0]
            if version in seen:
                continue
            path = os.path.join(MIGRATIONS_DIR, filename)
            with open(path, encoding="utf-8") as f:
                conn.execute(f.read())
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (version,),
            )
            applied.append(filename)
        conn.commit()
    return applied


def main() -> None:
    try:
        applied = apply_migrations()
        if applied:
            print("Applied schema migrations: " + ", ".join(applied))
        else:
            print("Schema is up to date")
    finally:
        close_pool()


if __name__ == "__main__":
    main()
