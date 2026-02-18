"""HITL and compliance gates for any live trade execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from apps.api.config import settings
from apps.api.db.broker_repo import log_trade_hitl_event


@dataclass
class HitlApproval:
    approved: bool
    reviewer: str
    ticket_id: str
    reason: str


def redact_order_payload(order_payload: dict[str, Any]) -> dict[str, Any]:
    """Redact verbose/sensitive fields before audit persistence."""
    allowed_keys = {
        "orderType",
        "session",
        "duration",
        "orderStrategyType",
        "price",
        "stopPrice",
        "orderLegCollection",
    }
    return {k: v for k, v in (order_payload or {}).items() if k in allowed_keys}


def enforce_trade_submission_allowed(
    *,
    approval: HitlApproval | None,
    hitl_shared_secret: str | None,
) -> None:
    """Raise HTTPException if live trade submission is not compliant."""
    if not settings.ENABLE_LIVE_TRADING:
        raise HTTPException(
            status_code=403,
            detail=(
                "Live order placement is disabled. Use preview endpoint only. "
                "Set ENABLE_LIVE_TRADING=true only when you are ready for manual HITL execution."
            ),
        )

    if settings.REQUIRE_HITL_FOR_TRADES:
        if not approval or not approval.approved:
            raise HTTPException(status_code=409, detail="HITL approval is required before any trade submission.")
        if not approval.reviewer or not approval.ticket_id or not approval.reason:
            raise HTTPException(status_code=409, detail="HITL metadata is incomplete (reviewer, ticket_id, reason).")

    if settings.HITL_SHARED_SECRET:
        if not hitl_shared_secret or hitl_shared_secret != settings.HITL_SHARED_SECRET:
            raise HTTPException(status_code=401, detail="Missing or invalid HITL shared secret.")


async def audit_trade_request(
    *,
    account_number: str | None,
    action: str,
    approval: HitlApproval | None,
    payload: dict[str, Any] | None,
) -> None:
    try:
        await log_trade_hitl_event(
            account_number=account_number,
            action=action,
            approved=bool(approval and approval.approved),
            reviewer=(approval.reviewer if approval else None),
            ticket_id=(approval.ticket_id if approval else None),
            reason=(approval.reason if approval else None),
            payload=redact_order_payload(payload or {}),
        )
    except Exception:
        # Audit persistence should not crash read-only workflows.
        return
