"""Portfolio database operations."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from apps.api.db.database import get_connection


async def _resolve_watchlist_table(conn) -> str:
    """Support both legacy `watchlist` and newer `watchlists` table names."""
    preferred = await conn.fetchval("SELECT to_regclass('public.watchlists')")
    if preferred:
        return "watchlists"
    legacy = await conn.fetchval("SELECT to_regclass('public.watchlist')")
    if legacy:
        return "watchlist"
    return "watchlists"


async def get_holdings(portfolio_id: str) -> list[dict]:
    """Get all holdings for a portfolio."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, symbol, shares, avg_cost, acquired_at, sector, notes, created_at
            FROM holdings
            WHERE portfolio_id = $1
            ORDER BY symbol
            """,
            UUID(portfolio_id),
        )
        return [dict(r) for r in rows]


async def upsert_holding(
    portfolio_id: str,
    symbol: str,
    shares: Decimal,
    avg_cost: Decimal,
    acquired_at=None,
    sector: str | None = None,
    notes: str | None = None,
) -> dict:
    """Insert or update a holding."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO holdings (portfolio_id, symbol, shares, avg_cost, acquired_at, sector, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (portfolio_id, symbol)
            DO UPDATE SET
                shares = EXCLUDED.shares,
                avg_cost = EXCLUDED.avg_cost,
                sector = COALESCE(EXCLUDED.sector, holdings.sector),
                notes = COALESCE(EXCLUDED.notes, holdings.notes),
                updated_at = NOW()
            RETURNING *
            """,
            UUID(portfolio_id), symbol.upper(), shares, avg_cost, acquired_at, sector, notes,
        )
        return dict(row)


async def delete_holding(portfolio_id: str, symbol: str) -> bool:
    """Remove a holding from a portfolio."""
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM holdings WHERE portfolio_id = $1 AND symbol = $2",
            UUID(portfolio_id), symbol.upper(),
        )
        return result == "DELETE 1"


async def add_transaction(
    portfolio_id: str,
    symbol: str,
    action: str,
    shares: Decimal,
    price: Decimal,
    fees: Decimal = Decimal("0"),
    executed_at=None,
    notes: str | None = None,
) -> dict:
    """Record a buy/sell/dividend transaction."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO transactions (portfolio_id, symbol, action, shares, price, fees, executed_at, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            UUID(portfolio_id), symbol.upper(), action, shares, price, fees, executed_at, notes,
        )
        return dict(row)


async def get_transactions(portfolio_id: str, symbol: str | None = None, limit: int = 50) -> list[dict]:
    """Get transaction history."""
    async with get_connection() as conn:
        if symbol:
            rows = await conn.fetch(
                """
                SELECT * FROM transactions
                WHERE portfolio_id = $1 AND symbol = $2
                ORDER BY executed_at DESC LIMIT $3
                """,
                UUID(portfolio_id), symbol.upper(), limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM transactions
                WHERE portfolio_id = $1
                ORDER BY executed_at DESC LIMIT $2
                """,
                UUID(portfolio_id), limit,
            )
        return [dict(r) for r in rows]


# ── Watchlist ─────────────────────────────────────────────

async def get_watchlist(user_id: str) -> list[dict]:
    """Get user's watchlist."""
    async with get_connection() as conn:
        table_name = await _resolve_watchlist_table(conn)
        rows = await conn.fetch(
            f"SELECT * FROM {table_name} WHERE user_id = $1 ORDER BY added_at DESC",
            UUID(user_id),
        )
        return [dict(r) for r in rows]


async def add_to_watchlist(
    user_id: str, symbol: str, target_low=None, target_high=None, notes=None,
) -> dict:
    """Add a symbol to watchlist."""
    async with get_connection() as conn:
        table_name = await _resolve_watchlist_table(conn)
        row = await conn.fetchrow(
            f"""
            INSERT INTO {table_name} (user_id, symbol, target_price_low, target_price_high, notes)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, symbol)
            DO UPDATE SET
                target_price_low = COALESCE(EXCLUDED.target_price_low, {table_name}.target_price_low),
                target_price_high = COALESCE(EXCLUDED.target_price_high, {table_name}.target_price_high),
                notes = COALESCE(EXCLUDED.notes, {table_name}.notes)
            RETURNING *
            """,
            UUID(user_id), symbol.upper(), target_low, target_high, notes,
        )
        return dict(row)


async def remove_from_watchlist(user_id: str, symbol: str) -> bool:
    """Remove a symbol from watchlist."""
    async with get_connection() as conn:
        table_name = await _resolve_watchlist_table(conn)
        result = await conn.execute(
            f"DELETE FROM {table_name} WHERE user_id = $1 AND symbol = $2",
            UUID(user_id), symbol.upper(),
        )
        return result == "DELETE 1"


# ── Alerts ────────────────────────────────────────────────

async def get_alerts(user_id: str, active_only: bool = True) -> list[dict]:
    """Get user's alerts."""
    async with get_connection() as conn:
        if active_only:
            rows = await conn.fetch(
                "SELECT * FROM alerts WHERE user_id = $1 AND is_active = TRUE ORDER BY created_at DESC",
                UUID(user_id),
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM alerts WHERE user_id = $1 ORDER BY created_at DESC",
                UUID(user_id),
            )
        return [dict(r) for r in rows]


async def create_alert(user_id: str, symbol: str, condition_type: str, threshold: dict, message: str | None = None) -> dict:
    """Create a new alert."""
    import json
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO alerts (user_id, symbol, condition_type, threshold, message)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            RETURNING *
            """,
            UUID(user_id), symbol.upper(), condition_type, json.dumps(threshold), message,
        )
        return dict(row)


async def delete_alert(user_id: str, alert_id: str) -> bool:
    """Remove an alert."""
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM alerts WHERE user_id = $1 AND id = $2",
            UUID(user_id), UUID(alert_id),
        )
        return result == "DELETE 1"
