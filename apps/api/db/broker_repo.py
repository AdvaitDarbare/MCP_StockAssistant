"""Broker API observability and HITL audit persistence."""

from __future__ import annotations

import json

from apps.api.db.database import get_connection


async def log_broker_event(
    *,
    provider: str,
    app_type: str,
    endpoint: str,
    method: str,
    status_code: int | None,
    attempt: int,
    latency_ms: int | None,
    success: bool,
    error: str | None = None,
    request_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO broker_api_events (
                provider, app_type, endpoint, method, status_code, attempt,
                latency_ms, success, error, request_id, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
            """,
            provider,
            app_type,
            endpoint,
            method,
            status_code,
            attempt,
            latency_ms,
            success,
            error,
            request_id,
            json.dumps(metadata or {}),
        )


async def log_trade_hitl_event(
    *,
    account_number: str | None,
    action: str,
    approved: bool,
    reviewer: str | None,
    ticket_id: str | None,
    reason: str | None,
    payload: dict | None,
) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO trade_hitl_audit (
                provider, account_number, action, approved,
                reviewer, ticket_id, reason, payload
            )
            VALUES ('schwab', $1, $2, $3, $4, $5, $6, $7::jsonb)
            """,
            account_number,
            action,
            approved,
            reviewer,
            ticket_id,
            reason,
            json.dumps(payload or {}),
        )
