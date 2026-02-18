"""Versioned SQL migration runner."""

from __future__ import annotations

import hashlib
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_LOCK_ID = 5_283_119


class MigrationError(RuntimeError):
    """Raised when a migration cannot be safely applied."""


def _checksum(sql_text: str) -> str:
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def _migration_files() -> list[Path]:
    return sorted(
        [p for p in MIGRATIONS_DIR.glob("*.sql") if p.is_file()],
        key=lambda p: p.name,
    )


async def run_migrations(pool: asyncpg.Pool) -> dict[str, int]:
    """Apply all pending SQL migrations exactly once."""
    applied_count = 0
    skipped_count = 0

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        await conn.execute("SELECT pg_advisory_lock($1)", MIGRATION_LOCK_ID)
        try:
            rows = await conn.fetch("SELECT version, checksum FROM schema_migrations")
            applied = {row["version"]: row["checksum"] for row in rows}

            for migration_file in _migration_files():
                version = migration_file.name
                sql = migration_file.read_text(encoding="utf-8")
                checksum = _checksum(sql)

                if version in applied:
                    if applied[version] != checksum:
                        raise MigrationError(
                            f"Checksum mismatch for already-applied migration {version}. "
                            "Create a new migration file instead of editing an applied one."
                        )
                    skipped_count += 1
                    continue

                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)",
                        version,
                        checksum,
                    )
                applied_count += 1
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", MIGRATION_LOCK_ID)

    return {"applied": applied_count, "skipped": skipped_count}
