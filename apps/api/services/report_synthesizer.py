"""Hybrid synthesis for report outputs using effective prompt instructions."""

from __future__ import annotations

import re
from typing import Any

from apps.api.agents.content_utils import truncate_text


def _first_meaningful_line(markdown: str) -> str:
    for line in (markdown or "").splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("#"):
            continue
        if candidate.startswith("|"):
            continue
        if candidate.strip().lower() == "[object object]":
            continue
        return candidate
    return "Report generated successfully."


def _extract_bullets(markdown: str, limit: int = 4) -> list[str]:
    bullets: list[str] = []
    for line in (markdown or "").splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.strip().lower() == "[object object]":
            continue
        if candidate.startswith("- ") or candidate.startswith("* "):
            bullets.append(candidate[2:].strip())
        elif re.match(r"^\d+\.\s+", candidate):
            bullets.append(re.sub(r"^\d+\.\s+", "", candidate).strip())
        if len(bullets) >= limit:
            break
    return bullets


def _render_evidence_table(sources: list[str], tool_plan: list[dict[str, Any]]) -> str:
    rows: list[tuple[str, str]] = []
    for source in sources[:6]:
        rows.append((source, "Data source"))
    for tool in tool_plan[:6]:
        rows.append((str(tool.get("tool", "tool")), str(tool.get("reason", "Used in orchestration"))))

    if not rows:
        return "_No explicit tool/source evidence was returned._"

    table_lines = [
        "| Evidence Item | Why it was used |",
        "|---|---|",
    ]
    for item, reason in rows:
        table_lines.append(f"| {item.replace('|', chr(92) + '|')} | {reason.replace('|', chr(92) + '|')} |")
    return "\n".join(table_lines)


def _clean_base_markdown(markdown: str) -> str:
    """Remove [object Object] artifacts and normalise whitespace."""
    cleaned = re.sub(r"\[object Object\]", "", markdown, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def synthesize_report_markdown(
    *,
    report: dict[str, Any],
    effective_prompt: str,
    follow_up_question: str | None = None,
    thread_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base_markdown = str(report.get("markdown", "") or "")
    assumptions = list(report.get("assumptions", []) or [])
    limitations = list(report.get("limitations", []) or [])

    # ── Clean, user-friendly output ──────────────────────────────────────
    parts: list[str] = []

    # Follow-up context (only if it's a follow-up)
    if follow_up_question:
        parts.append(f"**Follow-up Analysis:** {follow_up_question}")
        parts.append("")

    # Main report content
    clean_body = _clean_base_markdown(base_markdown)
    if clean_body:
        parts.append(clean_body)
    else:
        parts.append("Report generated successfully.")

    # Only show important caveats (simplified)
    important_caveats: list[str] = []
    if limitations:
        # Only show the first, most important limitation
        important_caveats.append(f"**Note:** {truncate_text(str(limitations[0]), 200)}")
    if assumptions and len(assumptions) > 0:
        # Only show if there are critical assumptions
        critical_assumptions = [a for a in assumptions if any(word in str(a).lower() for word in ['inferred', 'estimated', 'assumed'])]
        if critical_assumptions:
            important_caveats.append(f"**Assumption:** {truncate_text(str(critical_assumptions[0]), 200)}")

    if important_caveats:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.extend(important_caveats)

    synthesized = "\n".join(parts).strip()

    trace = {
        "phase": "synthesis",
        "status": "ok",
        "details": {
            "follow_up": bool(follow_up_question),
            "simplified_output": True,
        },
    }

    return {
        "markdown": synthesized,
        "trace": trace,
    }
