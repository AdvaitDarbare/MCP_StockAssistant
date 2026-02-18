"""Redis cache service with a module-level singleton connection pool.

Key design decisions:
- A single `CacheService` instance is created at startup via `init_cache()` and
  reused for the lifetime of the process.  This avoids the previous pattern of
  opening + closing a new Redis connection on every `cache_get_or_fetch` call.
- `redis.asyncio.from_url` already manages an internal connection pool, so we
  just need to stop recreating the client object.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

import redis.asyncio as redis

from apps.api.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton instance — initialised by init_cache() at app startup
# ---------------------------------------------------------------------------
_cache: "CacheService | None" = None


class CacheService:
    def __init__(self) -> None:
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache."""
        try:
            val = await self.redis.get(key)
            if val:
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return val
            return None
        except Exception as e:
            logger.warning("Cache GET error for key=%s: %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set a value in cache with TTL (seconds)."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.redis.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.warning("Cache SET error for key=%s: %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache DELETE error for key=%s: %s", key, e)
            return False

    async def close(self) -> None:
        """Close the underlying Redis connection pool."""
        await self.redis.aclose()


# ---------------------------------------------------------------------------
# Lifecycle helpers — called from the FastAPI lifespan context manager
# ---------------------------------------------------------------------------

async def init_cache() -> None:
    """Initialise the module-level cache singleton."""
    global _cache
    _cache = CacheService()
    logger.info("Redis cache pool initialised.")


async def close_cache() -> None:
    """Gracefully close the Redis connection pool."""
    global _cache
    if _cache is not None:
        await _cache.close()
        _cache = None
        logger.info("Redis cache pool closed.")


def get_cache() -> CacheService:
    """Return the singleton CacheService, creating it lazily if needed.

    The lazy fallback ensures the cache still works in test environments
    where `init_cache()` is not called via the lifespan.
    """
    global _cache
    if _cache is None:
        _cache = CacheService()
    return _cache


# ---------------------------------------------------------------------------
# TTL map
# ---------------------------------------------------------------------------

TTL_MAP = {
    "quote": 15,               # 15 seconds during market hours
    "quote_after_hours": 300,  # 5 minutes after hours
    "price_history": 3600,     # 1 hour
    "analyst_ratings": 86400,  # 1 day
    "sec_filings": 86400,      # 1 day
    "reddit_sentiment": 300,   # 5 minutes
    "economic_data": 3600,     # 1 hour
    "news": 300,               # 5 minutes
    "insider_trades": 3600,    # 1 hour
    "default": 60,             # 1 minute
}


async def cache_get_or_fetch(
    key: str,
    fetch_func: Callable,
    ttl_type: str = "default",
) -> Any:
    """Return cached value or call fetch_func, cache the result, and return it.

    Uses the module-level singleton — no per-call connection overhead.
    """
    cache = get_cache()
    try:
        cached = await cache.get(key)
        if cached is not None:
            return cached

        data = await fetch_func()

        if data is not None:
            ttl = TTL_MAP.get(ttl_type, 60)
            await cache.set(key, data, ttl=ttl)

        return data
    except Exception as e:
        logger.warning("Cache wrapper error for key=%s: %s — falling back to direct fetch", key, e)
        return await fetch_func()
