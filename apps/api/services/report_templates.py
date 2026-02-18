"""Prompt template resolution and override management for Report Lab."""

from __future__ import annotations

from apps.api.db.report_prompt_repo import (
    delete_override,
    get_override,
    get_overrides,
    upsert_override,
)
from apps.api.services.report_prompts import PROMPT_TEMPLATES

MAX_PROMPT_TEMPLATE_LENGTH = 24_000


def _normalize_report_type(report_type: str) -> str:
    rt = (report_type or "").strip().lower()
    if rt not in PROMPT_TEMPLATES:
        raise ValueError(f"Unknown report type '{report_type}'.")
    return rt


def _validate_owner_key(owner_key: str) -> str:
    key = (owner_key or "").strip()
    if not key:
        raise ValueError("owner_key is required.")
    if len(key) > 256:
        raise ValueError("owner_key is too long.")
    return key


def _validate_prompt_text(prompt_text: str) -> str:
    text = str(prompt_text or "").strip()
    if not text:
        raise ValueError("prompt_text is required.")
    if len(text) > MAX_PROMPT_TEMPLATE_LENGTH:
        raise ValueError(f"prompt_text exceeds max length {MAX_PROMPT_TEMPLATE_LENGTH}.")
    return text


async def list_templates(owner_key: str) -> list[dict[str, object]]:
    key = _validate_owner_key(owner_key)
    overrides = await get_overrides(key)
    templates: list[dict[str, object]] = []
    for report_type, meta in PROMPT_TEMPLATES.items():
        default_prompt = meta["prompt"]
        override = overrides.get(report_type)
        effective_prompt = override if override else default_prompt
        templates.append(
            {
                "id": report_type,
                "title": meta["title"],
                "default_prompt": default_prompt,
                "effective_prompt": effective_prompt,
                "is_overridden": bool(override),
            }
        )
    return templates


async def save_template_override(owner_key: str, report_type: str, prompt_text: str) -> dict:
    key = _validate_owner_key(owner_key)
    rt = _normalize_report_type(report_type)
    text = _validate_prompt_text(prompt_text)
    row = await upsert_override(key, rt, text)
    return {
        "owner_key": key,
        "id": rt,
        "title": PROMPT_TEMPLATES[rt]["title"],
        "effective_prompt": text,
        "is_overridden": True,
        "updated_at": row.get("updated_at"),
    }


async def reset_template_override(owner_key: str, report_type: str) -> dict:
    key = _validate_owner_key(owner_key)
    rt = _normalize_report_type(report_type)
    removed = await delete_override(key, rt)
    return {
        "owner_key": key,
        "id": rt,
        "title": PROMPT_TEMPLATES[rt]["title"],
        "effective_prompt": PROMPT_TEMPLATES[rt]["prompt"],
        "is_overridden": False,
        "removed": removed,
    }


async def get_effective_prompt(
    report_type: str,
    owner_key: str | None,
    inline_override: str | None = None,
) -> str:
    rt = _normalize_report_type(report_type)
    if inline_override and str(inline_override).strip():
        return _validate_prompt_text(str(inline_override))

    if owner_key:
        override = await get_override(owner_key.strip(), rt)
        if override and override.strip():
            return override

    return PROMPT_TEMPLATES[rt]["prompt"]
