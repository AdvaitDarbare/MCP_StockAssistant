"""MLflow tracking utilities for report orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from apps.api.config import settings

try:
    import mlflow  # type: ignore
except Exception:  # pragma: no cover
    mlflow = None


@dataclass
class MlflowRunResult:
    enabled: bool
    run_id: str | None = None
    error: str | None = None


def _compact_payload(payload: dict[str, Any], max_len: int = 500) -> str:
    text = str(payload)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _compact_text(value: str, max_len: int = 800) -> str:
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def log_report_run_to_mlflow(
    *,
    report_type: str,
    payload: dict[str, Any],
    result: dict[str, Any],
    generation_ms: int,
    quality_score: float,
    trace: dict[str, Any] | None = None,
) -> MlflowRunResult:
    if not settings.MLFLOW_ENABLED:
        return MlflowRunResult(enabled=False)
    if mlflow is None:
        return MlflowRunResult(enabled=False, error="mlflow package not installed")

    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        started = time.perf_counter()
        with mlflow.start_run(run_name=f"report:{report_type}") as run:
            mlflow.log_param("report_type", report_type)
            mlflow.log_param("payload", _compact_payload(payload))
            mlflow.log_param("has_ticker", bool(payload.get("ticker") or payload.get("symbol")))
            mlflow.log_metric("generation_ms", float(generation_ms))
            mlflow.log_metric("quality_score", float(quality_score))
            mlflow.log_metric("markdown_len", float(len(result.get("markdown", "") or "")))
            mlflow.log_metric("sources_count", float(len(result.get("sources_used", []) or [])))
            mlflow.log_metric("tool_plan_count", float(len(result.get("tool_plan", []) or [])))
            if trace:
                for key, value in trace.items():
                    mlflow.log_param(f"trace_{key}", _compact_text(str(value), 250))
            if result.get("markdown"):
                mlflow.log_text(str(result["markdown"]), artifact_file="report.md")
            mlflow.log_dict(result.get("data", {}), artifact_file="report_data.json")
            mlflow.log_dict(
                {
                    "assumptions": result.get("assumptions", []),
                    "limitations": result.get("limitations", []),
                    "sources_used": result.get("sources_used", []),
                    "tool_plan": result.get("tool_plan", []),
                    "trace": trace or {},
                },
                artifact_file="report_meta.json",
            )
        _ = int((time.perf_counter() - started) * 1000)
        return MlflowRunResult(enabled=True, run_id=run.info.run_id)
    except Exception as e:  # pragma: no cover
        return MlflowRunResult(enabled=True, error=str(e))


def log_chat_trace_to_mlflow(
    *,
    user_query: str,
    final_text: str,
    events: list[dict[str, Any]],
    duration_ms: int,
    route_agents: list[str],
    status: str = "ok",
    error: str | None = None,
) -> MlflowRunResult:
    if not settings.MLFLOW_ENABLED:
        return MlflowRunResult(enabled=False)
    if mlflow is None:
        return MlflowRunResult(enabled=False, error="mlflow package not installed")

    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_CHAT_EXPERIMENT_NAME)

        tool_events = [e for e in events if str(e.get("type", "")).startswith("tool_")]
        agent_events = [e for e in events if str(e.get("type", "")).startswith("agent_")]
        with mlflow.start_run(run_name="chat:supervisor") as run:
            mlflow.log_param("status", status)
            mlflow.log_param("route_agents", " -> ".join(route_agents))
            mlflow.log_param("user_query", _compact_text(user_query, 500))
            if error:
                mlflow.log_param("error", _compact_text(error, 500))

            mlflow.log_metric("duration_ms", float(duration_ms))
            mlflow.log_metric("event_count", float(len(events)))
            mlflow.log_metric("agent_event_count", float(len(agent_events)))
            mlflow.log_metric("tool_event_count", float(len(tool_events)))
            mlflow.log_metric("final_chars", float(len(final_text or "")))

            if final_text:
                mlflow.log_text(str(final_text), artifact_file="response.md")
            mlflow.log_dict(
                {
                    "user_query": user_query,
                    "status": status,
                    "error": error,
                    "route_agents": route_agents,
                    "events": events,
                },
                artifact_file="chat_trace.json",
            )
        return MlflowRunResult(enabled=True, run_id=run.info.run_id)
    except Exception as e:  # pragma: no cover
        return MlflowRunResult(enabled=True, error=str(e))
