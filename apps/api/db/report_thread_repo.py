"""Report thread persistence for follow-up interactions."""

from __future__ import annotations

import json
import uuid
from typing import Any

from apps.api.db.database import get_connection


def sanitize_uuid(uuid_str: str | None) -> str | None:
    """Sanitize UUID string by removing any prefixes and validating format."""
    if not uuid_str:
        return None
    
    # Remove any prefixes like 'conv-', 'user-', etc.
    if '-' in uuid_str and len(uuid_str) > 36:
        parts = uuid_str.split('-')
        if len(parts) >= 6:
            # Reconstruct UUID from parts (skip the first prefix part)
            uuid_parts = parts[1:]
            if len(uuid_parts) == 5:
                clean_uuid = '-'.join(uuid_parts)
                # Validate it's a proper UUID format (36 characters)
                if len(clean_uuid) == 36:
                    try:
                        # Validate it's a valid UUID
                        uuid.UUID(clean_uuid)
                        return clean_uuid
                    except ValueError:
                        pass
    
    # If it's already a proper UUID, validate and return it
    if len(uuid_str) == 36:
        try:
            uuid.UUID(uuid_str)
            return uuid_str
        except ValueError:
            pass
    
    # If we can't sanitize it, return None
    return None


async def create_thread(
    owner_key: str,
    report_type: str,
    base_payload: dict[str, Any],
    effective_prompt: str,
    latest_report: dict[str, Any],
) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO report_threads (owner_key, report_type, base_payload, effective_prompt, latest_report)
            VALUES ($1, $2, $3::jsonb, $4, $5::jsonb)
            RETURNING id, owner_key, report_type, base_payload, effective_prompt, latest_report, created_at, updated_at
            """,
            owner_key,
            report_type,
            json.dumps(base_payload or {}),
            effective_prompt,
            json.dumps(latest_report or {}),
        )
    return dict(row) if row else {}


async def get_thread(thread_id: str, owner_key: str | None = None) -> dict | None:
    if not thread_id:
        return None
    
    # Sanitize the thread_id
    clean_thread_id = sanitize_uuid(thread_id)
    if not clean_thread_id:
        return None
        
    async with get_connection() as conn:
        if owner_key:
            row = await conn.fetchrow(
                """
                SELECT id, owner_key, report_type, base_payload, effective_prompt, latest_report, created_at, updated_at
                FROM report_threads
                WHERE id = $1::uuid AND owner_key = $2
                """,
                clean_thread_id,
                owner_key,
            )
        else:
            row = await conn.fetchrow(
                """
                SELECT id, owner_key, report_type, base_payload, effective_prompt, latest_report, created_at, updated_at
                FROM report_threads
                WHERE id = $1::uuid
                """,
                clean_thread_id,
            )
    return dict(row) if row else None


async def update_thread_latest_report(thread_id: str, latest_report: dict[str, Any]) -> dict | None:
    clean_thread_id = sanitize_uuid(thread_id)
    if not clean_thread_id:
        return None
        
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            UPDATE report_threads
            SET latest_report = $2::jsonb,
                updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING id, owner_key, report_type, base_payload, effective_prompt, latest_report, created_at, updated_at
            """,
            clean_thread_id,
            json.dumps(latest_report or {}),
        )
    return dict(row) if row else None


async def append_thread_message(
    thread_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict:
    clean_thread_id = sanitize_uuid(thread_id)
    if not clean_thread_id:
        raise ValueError(f"Invalid thread_id format: {thread_id}")
        
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO report_thread_messages (thread_id, role, content, metadata)
            VALUES ($1::uuid, $2, $3, $4::jsonb)
            RETURNING id, thread_id, role, content, metadata, created_at
            """,
            clean_thread_id,
            role,
            content,
            json.dumps(metadata or {}),
        )
        await conn.execute(
            """
            UPDATE report_threads
            SET updated_at = NOW()
            WHERE id = $1::uuid
            """,
            clean_thread_id,
        )
    return dict(row) if row else {}


async def list_thread_messages(thread_id: str, limit: int = 30) -> list[dict]:
    clean_thread_id = sanitize_uuid(thread_id)
    if not clean_thread_id:
        return []
        
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, thread_id, role, content, metadata, created_at
            FROM report_thread_messages
            WHERE thread_id = $1::uuid
            ORDER BY created_at ASC
            LIMIT $2
            """,
            clean_thread_id,
            limit,
        )
    return [dict(row) for row in rows]
