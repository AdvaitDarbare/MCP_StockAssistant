"""Orchestrates report generation with quality gates and MLflow logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from apps.api.db.report_thread_repo import (
    append_thread_message,
    create_thread,
    get_thread,
    list_thread_messages,
    update_thread_latest_report,
)
from apps.api.services.mlflow_tracker import log_report_run_to_mlflow
from apps.api.services.report_engine import generate_report
from apps.api.services.report_synthesizer import synthesize_report_markdown
from apps.api.services.report_templates import get_effective_prompt

logger = logging.getLogger(__name__)


@dataclass
class ReportQuality:
    score: float
    checks: dict[str, bool]
    warnings: list[str]


@dataclass
class ReportRunOptions:
    owner_key: str | None = None
    prompt_override: str | None = None
    thread_id: str | None = None
    follow_up_question: str | None = None
    refresh_data: bool = False


def _score_quality(report: dict[str, Any], payload: dict[str, Any]) -> ReportQuality:
    markdown = str(report.get("markdown", "") or "")
    report_type = str(report.get("report_type", "") or "")
    sources = report.get("sources_used", []) or []
    tool_plan = report.get("tool_plan", []) or []
    ticker = str(payload.get("ticker") or payload.get("symbol") or "").upper()

    checks = {
        "has_markdown": len(markdown.strip()) > 120,
        "has_sources": len(sources) > 0,
        "has_tool_plan": len(tool_plan) > 0,
        "has_assumptions": len(report.get("assumptions", []) or []) > 0,
        "has_limitations": len(report.get("limitations", []) or []) > 0,
        "mentions_report_type": report_type.replace("_", " ")[:8].lower() in markdown.lower(),
        "mentions_ticker": (not ticker) or (ticker in markdown.upper()),
    }

    weights = {
        "has_markdown": 0.30,
        "has_sources": 0.15,
        "has_tool_plan": 0.15,
        "has_assumptions": 0.10,
        "has_limitations": 0.10,
        "mentions_report_type": 0.10,
        "mentions_ticker": 0.10,
    }
    score = sum(weights[k] for k, v in checks.items() if v)
    warnings = [k for k, v in checks.items() if not v]
    return ReportQuality(score=round(score, 3), checks=checks, warnings=warnings)


def _repair_if_needed(report: dict[str, Any], quality: ReportQuality) -> dict[str, Any]:
    repaired = dict(report)
    if not quality.checks.get("has_assumptions"):
        repaired["assumptions"] = ["Model assumptions are estimated from available market and fundamentals data."]
    if not quality.checks.get("has_limitations"):
        repaired["limitations"] = ["Some report sections use proxy metrics where direct datasets are unavailable."]
    if not quality.checks.get("has_sources"):
        repaired["sources_used"] = ["market_data_provider", "finviz"]
    if not quality.checks.get("has_tool_plan"):
        repaired["tool_plan"] = [{"tool": "report_engine", "reason": "Fallback tool plan"}]
    return repaired


def _normalize_options(options: ReportRunOptions | None) -> ReportRunOptions:
    if options is None:
        return ReportRunOptions()
    return options


async def _ensure_thread(
    *,
    owner_key: str,
    report_type: str,
    payload: dict[str, Any],
    effective_prompt: str,
    result: dict[str, Any],
    thread_id: str | None,
) -> str | None:
    """Get or create a report thread, returning the resolved thread_id.

    Consolidates the three nearly-identical create_thread call sites that
    previously existed in orchestrate_report (Q-2).
    """
    _create_kwargs = dict(
        owner_key=owner_key,
        report_type=report_type,
        base_payload=payload,
        effective_prompt=effective_prompt,
        latest_report=result,
    )
    if not thread_id:
        created = await create_thread(**_create_kwargs)
        return str(created.get("id", "")) or None

    try:
        existing = await get_thread(thread_id=thread_id, owner_key=owner_key)
        if not existing:
            created = await create_thread(**_create_kwargs)
            return str(created.get("id", "")) or None
        return thread_id
    except Exception as exc:
        logger.warning("Error checking thread %s, creating new one: %s", thread_id, exc)
        created = await create_thread(**_create_kwargs)
        return str(created.get("id", "")) or None


def _build_response_with_synthesis(
    *,
    report: dict[str, Any],
    effective_prompt: str,
    follow_up_question: str | None = None,
    thread_messages: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    synthesized = synthesize_report_markdown(
        report=report,
        effective_prompt=effective_prompt,
        follow_up_question=follow_up_question,
        thread_messages=thread_messages,
    )
    merged = dict(report)
    merged["markdown"] = synthesized["markdown"]
    return merged, synthesized["trace"]


async def orchestrate_report(
    report_type: str,
    payload: dict[str, Any],
    options: ReportRunOptions | None = None,
) -> dict[str, Any]:
    clean_payload = payload or {}
    opts = _normalize_options(options)
    started = time.perf_counter()
    trace: list[dict[str, Any]] = []

    effective_prompt = await get_effective_prompt(
        report_type=report_type,
        owner_key=opts.owner_key,
        inline_override=opts.prompt_override,
    )

    trace.append({"phase": "plan", "status": "ok", "details": "Selected report builder and tool plan."})
    result = await generate_report(report_type, clean_payload, effective_prompt=effective_prompt)
    trace.append({"phase": "generate", "status": "ok", "details": "Primary report generation complete."})
    result, synthesis_trace = _build_response_with_synthesis(
        report=result,
        effective_prompt=effective_prompt,
        follow_up_question=opts.follow_up_question,
        thread_messages=[],
    )
    trace.append(synthesis_trace)

    quality = _score_quality(result, clean_payload)
    trace.append(
        {
            "phase": "quality_gate",
            "status": "ok" if quality.score >= 0.75 else "warn",
            "details": {"score": quality.score, "warnings": quality.warnings},
        }
    )

    final_result = _repair_if_needed(result, quality)
    generation_ms = int((time.perf_counter() - started) * 1000)

    thread_id = opts.thread_id
    if opts.owner_key:
        thread_id = await _ensure_thread(
            owner_key=opts.owner_key,
            report_type=report_type,
            payload=clean_payload,
            effective_prompt=effective_prompt,
            result=final_result,
            thread_id=thread_id,
        )
        
        if thread_id:
            await append_thread_message(
                thread_id=thread_id,
                role="assistant",
                content=str(final_result.get("markdown", "")),
                metadata={"event": "initial_report", "report_type": report_type},
            )

    mlflow_result = log_report_run_to_mlflow(
        report_type=report_type,
        payload=clean_payload,
        result=final_result,
        generation_ms=generation_ms,
        quality_score=quality.score,
        trace={
            "owner_key": opts.owner_key or "",
            "thread_id": thread_id or "",
            "used_prompt_override": bool(opts.prompt_override),
            "refresh_data": bool(opts.refresh_data),
            "report_type": report_type,
        },
    )
    trace.append(
        {
            "phase": "mlflow",
            "status": "ok" if not mlflow_result.error else "warn",
            "details": {
                "enabled": mlflow_result.enabled,
                "run_id": mlflow_result.run_id,
                "error": mlflow_result.error,
            },
        }
    )

    final_result["quality_gate"] = {
        "score": quality.score,
        "checks": quality.checks,
        "warnings": quality.warnings,
    }
    final_result["orchestration_trace"] = trace
    final_result["generation_ms"] = generation_ms
    final_result["effective_prompt"] = effective_prompt
    final_result["thread_id"] = thread_id
    final_result["follow_up_supported"] = True
    if mlflow_result.run_id:
        final_result["mlflow_run_id"] = mlflow_result.run_id
    return final_result


async def orchestrate_report_followup(
    report_type: str,
    *,
    owner_key: str,
    thread_id: str,
    question: str,
    refresh_data: bool = False,
) -> dict[str, Any]:
    if not owner_key or not owner_key.strip():
        raise ValueError("owner_key is required for report follow-up.")
    if not thread_id or not thread_id.strip():
        raise ValueError("thread_id is required for report follow-up.")
    if not question or not question.strip():
        raise ValueError("question is required for report follow-up.")

    started = time.perf_counter()
    trace: list[dict[str, Any]] = [
        {
            "phase": "followup_plan",
            "status": "ok",
            "details": {"thread_id": thread_id, "refresh_data": refresh_data},
        }
    ]

    thread = await get_thread(thread_id=thread_id, owner_key=owner_key)
    if not thread:
        raise ValueError("Report thread not found for this owner.")

    if str(thread.get("report_type", "")).lower() != report_type.strip().lower():
        raise ValueError("Thread report type does not match endpoint report type.")

    base_payload = dict(thread.get("base_payload") or {})
    effective_prompt = str(thread.get("effective_prompt") or "")
    latest_report = dict(thread.get("latest_report") or {})

    await append_thread_message(
        thread_id=thread_id,
        role="user",
        content=question,
        metadata={"event": "followup"},
    )

    working_report = latest_report
    if refresh_data:
        refreshed = await generate_report(report_type, base_payload, effective_prompt=effective_prompt)
        trace.append({"phase": "generate_refresh", "status": "ok", "details": "Refreshed deterministic report data."})
        working_report = refreshed

    thread_messages = await list_thread_messages(thread_id, limit=40)
    working_report, synthesis_trace = _build_response_with_synthesis(
        report=working_report,
        effective_prompt=effective_prompt,
        follow_up_question=question,
        thread_messages=thread_messages,
    )
    trace.append(synthesis_trace)

    quality = _score_quality(working_report, base_payload)
    final_result = _repair_if_needed(working_report, quality)
    await update_thread_latest_report(thread_id, final_result)
    await append_thread_message(
        thread_id=thread_id,
        role="assistant",
        content=str(final_result.get("markdown", "")),
        metadata={"event": "followup_response"},
    )

    generation_ms = int((time.perf_counter() - started) * 1000)
    mlflow_result = log_report_run_to_mlflow(
        report_type=report_type,
        payload=base_payload,
        result=final_result,
        generation_ms=generation_ms,
        quality_score=quality.score,
        trace={
            "owner_key": owner_key,
            "thread_id": thread_id,
            "used_prompt_override": False,
            "refresh_data": refresh_data,
            "report_type": report_type,
            "follow_up": True,
        },
    )
    trace.append(
        {
            "phase": "mlflow",
            "status": "ok" if not mlflow_result.error else "warn",
            "details": {
                "enabled": mlflow_result.enabled,
                "run_id": mlflow_result.run_id,
                "error": mlflow_result.error,
            },
        }
    )

    final_result["quality_gate"] = {
        "score": quality.score,
        "checks": quality.checks,
        "warnings": quality.warnings,
    }
    final_result["orchestration_trace"] = trace
    final_result["generation_ms"] = generation_ms
    final_result["effective_prompt"] = effective_prompt
    final_result["thread_id"] = thread_id
    final_result["follow_up_supported"] = True
    final_result["follow_up_question"] = question
    if mlflow_result.run_id:
        final_result["mlflow_run_id"] = mlflow_result.run_id
    return final_result
