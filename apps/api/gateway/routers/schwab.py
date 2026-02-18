from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from apps.api.services.schwab_client import (
    build_schwab_authorize_url,
    exchange_auth_code_for_token,
    get_account_orders,
    get_account_transactions,
    get_accounts,
    get_all_orders,
    get_schwab_observability_snapshot,
    place_order,
    preview_order,
    refresh_auth_token,
    get_user_preferences,
    schwab_connection_status,
)
from apps.api.services.trade_controls import (
    HitlApproval,
    audit_trade_request,
    enforce_trade_submission_allowed,
)

router = APIRouter()


def _unavailable(detail: str, app: str = "trader") -> HTTPException:
    status = schwab_connection_status()
    app_status = status.get(app, {})
    last_error = app_status.get("last_error")
    if last_error:
        return HTTPException(status_code=503, detail=f"{detail} Last error: {last_error}")
    return HTTPException(status_code=503, detail=detail)


class SchwabCodeExchangeRequest(BaseModel):
    code: str
    redirect_uri: str | None = None
    app: str = "market"


class SchwabRefreshRequest(BaseModel):
    refresh_token: str | None = None
    app: str = "market"


class HitlApprovalRequest(BaseModel):
    approved: bool = False
    reviewer: str = ""
    ticket_id: str = ""
    reason: str = ""


class OrderSubmissionRequest(BaseModel):
    order: dict
    hitl: HitlApprovalRequest | None = None


@router.get("/schwab/status")
async def schwab_status():
    return schwab_connection_status()


@router.get("/schwab/oauth/authorize-url")
async def schwab_authorize_url(scope: str = "readonly", state: str | None = None, app: str = "market"):
    status = schwab_connection_status()
    if app == "trader":
        if not status["trader"]["configured"]:
            raise HTTPException(status_code=400, detail="Schwab trader app is not configured.")
    else:
        if not status["market"]["configured"]:
            raise HTTPException(status_code=400, detail="Schwab market app is not configured.")
    url = build_schwab_authorize_url(scope=scope, state=state, app_type=app)
    return {"authorize_url": url}


@router.post("/schwab/oauth/exchange")
async def schwab_oauth_exchange(request: SchwabCodeExchangeRequest):
    token = await exchange_auth_code_for_token(
        code=request.code,
        redirect_uri=request.redirect_uri,
        app_type=request.app,
    )
    if not token:
        raise HTTPException(status_code=503, detail="Token exchange failed.")
    if token.get("error"):
        raise HTTPException(status_code=400, detail=token)
    return {
        "status": "ok",
        "token_saved": True,
        "expires_in": token.get("expires_in"),
        "app": request.app,
    }


@router.post("/schwab/oauth/refresh")
async def schwab_oauth_refresh(request: SchwabRefreshRequest):
    token = await refresh_auth_token(
        refresh_token=request.refresh_token,
        app_type=request.app,
    )
    if not token:
        raise HTTPException(status_code=503, detail="Token refresh failed.")
    if token.get("error"):
        raise HTTPException(status_code=400, detail=token)
    return {
        "status": "ok",
        "token_saved": True,
        "expires_in": token.get("expires_in"),
        "app": request.app,
    }


@router.get("/schwab/accounts")
async def schwab_accounts(include_positions: bool = True):
    data = await get_accounts(include_positions=include_positions)
    if data is None:
        raise _unavailable("Schwab accounts unavailable. Check credentials/token.", app="trader")
    return {"accounts": data}


@router.get("/schwab/accounts/{account_number}/positions")
async def schwab_positions(account_number: str):
    data = await get_accounts(include_positions=True)
    if data is None:
        raise _unavailable("Schwab accounts unavailable. Check credentials/token.", app="trader")
    for account in data:
        securities = account.get("securitiesAccount") or account.get("account") or account
        acct_num = str(securities.get("accountNumber") or securities.get("account_number") or "")
        if acct_num == str(account_number):
            return {
                "account_number": account_number,
                "positions": securities.get("positions", []),
            }
    raise HTTPException(status_code=404, detail=f"Account {account_number} not found in Schwab response.")


@router.get("/schwab/orders")
async def schwab_orders(max_results: int = Query(default=100, ge=1, le=1000)):
    data = await get_all_orders(max_results=max_results)
    if data is None:
        raise _unavailable("Schwab orders unavailable.", app="trader")
    return {"orders": data}


@router.get("/schwab/accounts/{account_number}/orders")
async def schwab_account_orders(account_number: str, max_results: int = Query(default=100, ge=1, le=1000)):
    data = await get_account_orders(account_number, max_results=max_results)
    if data is None:
        raise _unavailable("Schwab account orders unavailable.", app="trader")
    return {"account_number": account_number, "orders": data}


@router.get("/schwab/accounts/{account_number}/transactions")
async def schwab_transactions(account_number: str, max_results: int = Query(default=100, ge=1, le=1000)):
    data = await get_account_transactions(account_number, max_results=max_results)
    if data is None:
        raise _unavailable("Schwab transactions unavailable.", app="trader")
    return {"account_number": account_number, "transactions": data}


@router.get("/schwab/user-preference")
async def schwab_user_preference():
    data = await get_user_preferences()
    if data is None:
        raise _unavailable("Schwab user preference unavailable.", app="trader")
    return data


@router.get("/schwab/observability")
async def schwab_observability(limit: int = Query(default=50, ge=1, le=200)):
    return get_schwab_observability_snapshot(limit=limit)


@router.post("/schwab/accounts/{account_number}/orders/preview")
async def schwab_preview_order(account_number: str, request: OrderSubmissionRequest):
    await audit_trade_request(
        account_number=account_number,
        action="preview",
        approval=(
            HitlApproval(
                approved=request.hitl.approved,
                reviewer=request.hitl.reviewer,
                ticket_id=request.hitl.ticket_id,
                reason=request.hitl.reason,
            )
            if request.hitl
            else None
        ),
        payload=request.order,
    )
    data = await preview_order(account_number, request.order)
    if data is None:
        raise _unavailable("Schwab preview unavailable.", app="trader")
    return {"account_number": account_number, "preview": data}


@router.post("/schwab/accounts/{account_number}/orders/submit")
async def schwab_submit_order(
    account_number: str,
    request: OrderSubmissionRequest,
    x_hitl_secret: str | None = Header(default=None),
):
    approval = (
        HitlApproval(
            approved=request.hitl.approved,
            reviewer=request.hitl.reviewer,
            ticket_id=request.hitl.ticket_id,
            reason=request.hitl.reason,
        )
        if request.hitl
        else None
    )
    await audit_trade_request(
        account_number=account_number,
        action="submit_attempt",
        approval=approval,
        payload=request.order,
    )
    enforce_trade_submission_allowed(
        approval=approval,
        hitl_shared_secret=x_hitl_secret,
    )
    data = await place_order(account_number, request.order)
    if data is None:
        raise _unavailable("Schwab order submission failed.", app="trader")
    await audit_trade_request(
        account_number=account_number,
        action="submit_success",
        approval=approval,
        payload=request.order,
    )
    return {"account_number": account_number, "result": data, "status": "submitted"}
