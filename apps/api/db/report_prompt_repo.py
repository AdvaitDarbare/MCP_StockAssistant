"""Report prompt override persistence."""

from __future__ import annotations

from apps.api.db.database import get_connection


async def get_overrides(owner_key: str) -> dict[str, str]:
    if not owner_key:
        return {}
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT report_type, prompt_text
            FROM report_prompt_overrides
            WHERE owner_key = $1
            """,
            owner_key,
        )
    return {str(row["report_type"]): str(row["prompt_text"]) for row in rows}


async def get_override(owner_key: str, report_type: str) -> str | None:
    if not owner_key or not report_type:
        return None
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT prompt_text
            FROM report_prompt_overrides
            WHERE owner_key = $1 AND report_type = $2
            """,
            owner_key,
            report_type,
        )
    return str(row["prompt_text"]) if row else None


async def upsert_override(owner_key: str, report_type: str, prompt_text: str) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO report_prompt_overrides (owner_key, report_type, prompt_text)
            VALUES ($1, $2, $3)
            ON CONFLICT (owner_key, report_type)
            DO UPDATE SET
                prompt_text = EXCLUDED.prompt_text,
                updated_at = NOW()
            RETURNING id, owner_key, report_type, prompt_text, created_at, updated_at
            """,
            owner_key,
            report_type,
            prompt_text,
        )
    return dict(row) if row else {}


async def delete_override(owner_key: str, report_type: str) -> bool:
    async with get_connection() as conn:
        result = await conn.execute(
            """
            DELETE FROM report_prompt_overrides
            WHERE owner_key = $1 AND report_type = $2
            """,
            owner_key,
            report_type,
        )
    return result.endswith("1")
