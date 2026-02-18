"""Report persistence operations."""

from __future__ import annotations

import json

from apps.api.db.database import get_connection


async def save_report_run(report_type: str, payload: dict, report: dict) -> dict | None:
    """Persist generated report payload/output for reproducibility."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO report_runs (report_type, payload, report)
            VALUES ($1, $2::jsonb, $3::jsonb)
            RETURNING id, report_type, generated_at
            """,
            report_type,
            json.dumps(payload or {}),
            json.dumps(report or {}),
        )
        return dict(row) if row else None


async def get_report_run(run_id: str) -> dict | None:
    """Get a persisted report run by id."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, report_type, payload, report, generated_at
            FROM report_runs
            WHERE id = $1::uuid
            """,
            run_id,
        )
    return dict(row) if row else None
