"""Database connection management for Postgres."""

import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apps.api.config import settings
from apps.api.db.migrations import run_migrations

_pool: asyncpg.Pool | None = None


async def init_db():
    """Initialize the database connection pool."""
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"),
        min_size=2,
        max_size=10,
    )
    await run_migrations(_pool)


async def close_db():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the connection pool."""
    if _pool is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool."""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn
