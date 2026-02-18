"""Schwab API client with dual app support, retries, and observability."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import httpx

from apps.api.config import settings
from apps.api.db.broker_repo import log_broker_event
from apps.api.services.cache import cache_get_or_fetch

logger = logging.getLogger(__name__)

AUTH_BASE_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
MARKETDATA_BASE_URL = "https://api.schwabapi.com/marketdata/v1"
TRADER_BASE_URL = "https://api.schwabapi.com/trader/v1"

APP_MARKET = "market"
APP_TRADER = "trader"
APP_TYPES = {APP_MARKET, APP_TRADER}

_OBS_EVENTS: deque[dict] = deque(maxlen=settings.SCHWAB_OBSERVABILITY_BUFFER_SIZE)
_OBS_COUNTERS: defaultdict[str, int] = defaultdict(int)
_LAST_ERRORS: dict[str, str | None] = {APP_MARKET: None, APP_TRADER: None}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_app_type(app_type: str | None) -> str:
    app = (app_type or APP_MARKET).strip().lower()
    return app if app in APP_TYPES else APP_MARKET


def _credentials(app_type: str) -> tuple[str, str]:
    app = _normalize_app_type(app_type)
    if app == APP_TRADER:
        return settings.SCHWAB_TRADER_CLIENT_ID, settings.SCHWAB_TRADER_CLIENT_SECRET
    return settings.SCHWAB_MARKET_CLIENT_ID, settings.SCHWAB_MARKET_CLIENT_SECRET


def _token_path(app_type: str) -> Path:
    app = _normalize_app_type(app_type)
    if app == APP_TRADER:
        return Path(settings.SCHWAB_TRADER_TOKEN_PATH)
    return Path(settings.SCHWAB_MARKET_TOKEN_PATH)


def _service_default_app(service: str) -> str:
    return APP_TRADER if service == "trader" else APP_MARKET


def _token_is_expired(token_payload: dict, token_file: Path) -> bool:
    expires_in = int(token_payload.get("expires_in", 0) or 0)
    if expires_in <= 0:
        return True
    if not token_file.exists():
        return True
    issued_at = token_file.stat().st_mtime
    return time.time() >= (issued_at + expires_in - 60)


def _read_token_file(app_type: str) -> dict | None:
    path = _token_path(app_type)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _write_token_file(app_type: str, token_payload: dict) -> None:
    path = _token_path(app_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token_payload, indent=2))


def _retry_delay(attempt: int) -> float:
    base = max(0.05, settings.SCHWAB_RETRY_BACKOFF_SECONDS)
    jitter = random.uniform(0, 0.1)
    return base * (2 ** (attempt - 1)) + jitter


async def _record_event(
    *,
    app_type: str,
    endpoint: str,
    method: str,
    status_code: int | None,
    attempt: int,
    latency_ms: int | None,
    success: bool,
    error: str | None,
    request_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    event = {
        "timestamp": _now_iso(),
        "provider": "schwab",
        "app_type": app_type,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "attempt": attempt,
        "latency_ms": latency_ms,
        "success": success,
        "error": error,
        "request_id": request_id,
    }
    _OBS_EVENTS.append(event)
    counter_key = f"{app_type}:{method}:{endpoint}:{status_code or 'ERR'}"
    _OBS_COUNTERS[counter_key] += 1

    if error:
        _LAST_ERRORS[app_type] = error
    elif success:
        _LAST_ERRORS[app_type] = None

    async def _persist() -> None:
        try:
            await log_broker_event(
                provider="schwab",
                app_type=app_type,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                attempt=attempt,
                latency_ms=latency_ms,
                success=success,
                error=error,
                request_id=request_id,
                metadata=metadata or {},
            )
        except Exception as exc:  # pragma: no cover - non-critical telemetry.
            logger.debug("Failed to persist Schwab broker event: %s", exc)

    asyncio.create_task(_persist())


async def _request_with_retry(
    *,
    method: str,
    url: str,
    app_type: str,
    endpoint: str,
    headers: dict[str, str] | None = None,
    params: dict | None = None,
    data: dict | None = None,
    json_body: dict | None = None,
) -> httpx.Response | None:
    attempts = max(1, settings.SCHWAB_MAX_RETRIES)
    retry_statuses = {
        httpx.codes.TOO_MANY_REQUESTS,
        httpx.codes.BAD_GATEWAY,
        httpx.codes.SERVICE_UNAVAILABLE,
        httpx.codes.GATEWAY_TIMEOUT,
    }

    async with httpx.AsyncClient(timeout=settings.SCHWAB_HTTP_TIMEOUT_SECONDS) as client:
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_body,
                )
                latency_ms = int((time.perf_counter() - started) * 1000)
                request_id = response.headers.get("x-request-id") or response.headers.get("request-id")
                await _record_event(
                    app_type=app_type,
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status_code,
                    attempt=attempt,
                    latency_ms=latency_ms,
                    success=response.status_code < 400,
                    error=None if response.status_code < 400 else response.text[:300],
                    request_id=request_id,
                )

                if response.status_code in retry_statuses and attempt < attempts:
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
                latency_ms = int((time.perf_counter() - started) * 1000)
                error_text = f"{type(exc).__name__}: {exc}"
                await _record_event(
                    app_type=app_type,
                    endpoint=endpoint,
                    method=method,
                    status_code=None,
                    attempt=attempt,
                    latency_ms=latency_ms,
                    success=False,
                    error=error_text,
                )
                if attempt >= attempts:
                    _LAST_ERRORS[app_type] = error_text
                    return None
                await asyncio.sleep(_retry_delay(attempt))
    return None


async def _refresh_if_needed(app_type: str, token_data: dict) -> dict | None:
    path = _token_path(app_type)
    if _token_is_expired(token_data, path):
        refreshed = await refresh_auth_token(app_type=app_type)
        if not refreshed or refreshed.get("error"):
            return None
        return refreshed
    return token_data


async def _get_valid_access_token(app_type: str) -> str | None:
    token_data = _read_token_file(app_type) or {}
    if not token_data:
        return None

    token_data = await _refresh_if_needed(app_type, token_data)
    if not token_data:
        return None

    return token_data.get("access_token")


def get_schwab_observability_snapshot(limit: int = 50) -> dict:
    recent = list(_OBS_EVENTS)[-max(1, min(limit, settings.SCHWAB_OBSERVABILITY_BUFFER_SIZE)) :]
    return {
        "buffer_size": settings.SCHWAB_OBSERVABILITY_BUFFER_SIZE,
        "event_count": len(_OBS_EVENTS),
        "recent_events": recent,
        "counters": dict(sorted(_OBS_COUNTERS.items())),
        "last_errors": dict(_LAST_ERRORS),
    }


def schwab_connection_status() -> dict:
    market_id, market_secret = _credentials(APP_MARKET)
    trader_id, trader_secret = _credentials(APP_TRADER)
    market_token_path = str(_token_path(APP_MARKET))
    trader_token_path = str(_token_path(APP_TRADER))
    market_token_exists = _token_path(APP_MARKET).exists()
    trader_token_exists = _token_path(APP_TRADER).exists()

    return {
        "configured": bool(market_id and market_secret),
        "token_exists": market_token_exists,
        "client_ready": market_token_exists,
        "redirect_uri": settings.SCHWAB_REDIRECT_URI,
        "token_path": market_token_path,
        "market": {
            "configured": bool(market_id and market_secret),
            "token_exists": market_token_exists,
            "client_ready": market_token_exists,
            "redirect_uri": settings.SCHWAB_REDIRECT_URI,
            "token_path": market_token_path,
            "client_id_suffix": market_id[-4:] if market_id else "",
            "last_error": _LAST_ERRORS[APP_MARKET],
        },
        "trader": {
            "configured": bool(trader_id and trader_secret),
            "token_exists": trader_token_exists,
            "client_ready": trader_token_exists,
            "redirect_uri": settings.SCHWAB_REDIRECT_URI,
            "token_path": trader_token_path,
            "client_id_suffix": trader_id[-4:] if trader_id else "",
            "last_error": _LAST_ERRORS[APP_TRADER],
        },
        "retry_policy": {
            "timeout_seconds": settings.SCHWAB_HTTP_TIMEOUT_SECONDS,
            "max_retries": settings.SCHWAB_MAX_RETRIES,
            "base_backoff_seconds": settings.SCHWAB_RETRY_BACKOFF_SECONDS,
        },
    }


def build_schwab_authorize_url(
    scope: str = "readonly",
    state: str | None = None,
    app_type: str = APP_MARKET,
) -> str:
    client_id, _ = _credentials(app_type)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": settings.SCHWAB_REDIRECT_URI,
        "scope": scope,
    }
    if state:
        params["state"] = state
    return f"{AUTH_BASE_URL}?{urlencode(params)}"


async def exchange_auth_code_for_token(
    code: str,
    redirect_uri: str | None = None,
    app_type: str = APP_MARKET,
) -> dict | None:
    app = _normalize_app_type(app_type)
    client_id, client_secret = _credentials(app)
    if not client_id or not client_secret:
        return {"error": f"Missing Schwab credentials for app '{app}'"}

    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or settings.SCHWAB_REDIRECT_URI,
    }

    resp = await _request_with_retry(
        method="POST",
        url=TOKEN_URL,
        app_type=app,
        endpoint="/oauth/token",
        headers=headers,
        data=data,
    )
    if not resp:
        return {"error": "Token exchange failed: network/timeout"}
    if resp.status_code != httpx.codes.OK:
        return {"error": f"Token exchange failed: {resp.status_code}", "body": resp.text}

    payload = resp.json()
    _write_token_file(app, payload)
    return payload


async def refresh_auth_token(
    refresh_token: str | None = None,
    app_type: str = APP_MARKET,
) -> dict | None:
    app = _normalize_app_type(app_type)
    token_data = _read_token_file(app) or {}
    rt = refresh_token or token_data.get("refresh_token")
    if not rt:
        return {"error": "No refresh token available"}

    client_id, client_secret = _credentials(app)
    if not client_id or not client_secret:
        return {"error": f"Missing Schwab credentials for app '{app}'"}

    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "refresh_token", "refresh_token": rt}

    resp = await _request_with_retry(
        method="POST",
        url=TOKEN_URL,
        app_type=app,
        endpoint="/oauth/token",
        headers=headers,
        data=data,
    )
    if not resp:
        return {"error": "Token refresh failed: network/timeout"}
    if resp.status_code != httpx.codes.OK:
        return {"error": f"Token refresh failed: {resp.status_code}", "body": resp.text}

    payload = resp.json()
    merged = {**token_data, **payload}
    _write_token_file(app, merged)
    return merged


async def _schwab_get(
    path: str,
    params: dict | None = None,
    service: str = "marketdata",
    app_type: str | None = None,
    retry_on_401: bool = True,
) -> dict | list | None:
    app = _normalize_app_type(app_type or _service_default_app(service))
    access_token = await _get_valid_access_token(app)
    if not access_token:
        _LAST_ERRORS[app] = "No valid access token"
        return None

    base_url = MARKETDATA_BASE_URL if service == "marketdata" else TRADER_BASE_URL
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{base_url}{path}"

    resp = await _request_with_retry(
        method="GET",
        url=url,
        app_type=app,
        endpoint=path,
        headers=headers,
        params=params,
    )
    if not resp:
        return None

    if resp.status_code == httpx.codes.UNAUTHORIZED and retry_on_401:
        refreshed = await refresh_auth_token(app_type=app)
        if refreshed and not refreshed.get("error"):
            return await _schwab_get(
                path,
                params=params,
                service=service,
                app_type=app,
                retry_on_401=False,
            )
    if resp.status_code != httpx.codes.OK:
        _LAST_ERRORS[app] = f"HTTP {resp.status_code}: {resp.text[:300]}"
        return None
    try:
        return resp.json()
    except Exception:
        _LAST_ERRORS[app] = "Failed to decode response JSON"
        return None


async def _schwab_post(
    path: str,
    payload: dict,
    service: str = "trader",
    app_type: str | None = None,
    expected_status: set[int] | None = None,
    retry_on_401: bool = True,
) -> dict | list | None:
    app = _normalize_app_type(app_type or _service_default_app(service))
    access_token = await _get_valid_access_token(app)
    if not access_token:
        _LAST_ERRORS[app] = "No valid access token"
        return None

    base_url = MARKETDATA_BASE_URL if service == "marketdata" else TRADER_BASE_URL
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = f"{base_url}{path}"
    expected = expected_status or {httpx.codes.OK, httpx.codes.CREATED, httpx.codes.ACCEPTED}

    resp = await _request_with_retry(
        method="POST",
        url=url,
        app_type=app,
        endpoint=path,
        headers=headers,
        json_body=payload,
    )
    if not resp:
        return None

    if resp.status_code == httpx.codes.UNAUTHORIZED and retry_on_401:
        refreshed = await refresh_auth_token(app_type=app)
        if refreshed and not refreshed.get("error"):
            return await _schwab_post(
                path,
                payload=payload,
                service=service,
                app_type=app,
                expected_status=expected,
                retry_on_401=False,
            )
    if resp.status_code not in expected:
        _LAST_ERRORS[app] = f"HTTP {resp.status_code}: {resp.text[:300]}"
        return None

    try:
        return resp.json()
    except Exception:
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text,
        }


def _extract_quote(data: dict, symbol: str) -> dict | None:
    sym = symbol.upper()
    if sym not in data or "quote" not in data[sym]:
        return None
    q = data[sym]["quote"]
    return {
        "symbol": sym,
        "price": q.get("lastPrice"),
        "change": q.get("netChange"),
        "percent_change": q.get("netPercentChange"),
        "volume": q.get("totalVolume"),
        "bid": q.get("bidPrice"),
        "ask": q.get("askPrice"),
        "open": q.get("openPrice"),
        "close": q.get("closePrice"),
        "high": q.get("highPrice"),
        "low": q.get("lowPrice"),
        "week_52_high": q.get("52WeekHigh"),
        "week_52_low": q.get("52WeekLow"),
        "pe_ratio": q.get("peRatio"),
        "dividend_yield": q.get("divYield"),
        "trade_time": datetime.fromtimestamp(q["tradeTime"] / 1000).isoformat() if q.get("tradeTime") else None,
    }


async def get_quote(symbol: str) -> dict | None:
    async def _fetch():
        data = await _schwab_get(
            "/quotes",
            params={"symbols": symbol.upper()},
            service="marketdata",
            app_type=APP_MARKET,
        )
        if not isinstance(data, dict):
            return None
        return _extract_quote(data, symbol)

    return await cache_get_or_fetch(f"quote:{symbol.upper()}", _fetch, "quote")


async def get_multiple_quotes(symbols: list[str]) -> dict:
    data = await _schwab_get(
        "/quotes",
        params={"symbols": ",".join([s.upper() for s in symbols])},
        service="marketdata",
        app_type=APP_MARKET,
    )
    if not isinstance(data, dict):
        return {}
    out = {}
    for symbol in symbols:
        q = _extract_quote(data, symbol)
        if q:
            out[symbol.upper()] = q
    return out


async def get_price_history(
    symbol: str,
    period_type: str = "month",
    period: int = 1,
    frequency_type: str = "daily",
    frequency: int = 1,
) -> dict | None:
    cache_key = f"history:{symbol.upper()}:{period_type}:{period}:{frequency_type}:{frequency}"

    async def _fetch():
        data = await _schwab_get(
            "/pricehistory",
            params={
                "symbol": symbol.upper(),
                "periodType": period_type,
                "period": period,
                "frequencyType": frequency_type,
                "frequency": frequency,
            },
            service="marketdata",
            app_type=APP_MARKET,
        )
        if not isinstance(data, dict) or not data.get("candles"):
            return None
        return {
            "symbol": symbol.upper(),
            "candles": [
                {
                    "datetime": datetime.fromtimestamp(c["datetime"] / 1000).isoformat(),
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                    "volume": c["volume"],
                }
                for c in data["candles"]
            ],
            "period_type": period_type,
            "period": period,
            "frequency_type": frequency_type,
            "frequency": frequency,
        }

    return await cache_get_or_fetch(cache_key, _fetch, "price_history")


async def get_market_movers(
    index: str = "$SPX",
    sort: str = "PERCENT_CHANGE_UP",
    frequency: int = 0,
) -> dict | None:
    cache_key = f"movers:{index}:{sort}:{frequency}"

    async def _fetch():
        params = {"sort": sort}
        if frequency > 0:
            params["frequency"] = frequency
        data = await _schwab_get(
            f"/movers/{index}",
            params=params,
            service="marketdata",
            app_type=APP_MARKET,
        )
        if not isinstance(data, dict):
            return None

        screeners = data.get("screeners")
        if screeners is None and isinstance(data.get("movers"), list):
            screeners = data.get("movers")
        if screeners is None and isinstance(data, list):
            screeners = data
        if not screeners:
            return None

        return {
            "index": index,
            "sort": sort,
            "movers": [
                {
                    "symbol": m.get("symbol"),
                    "description": m.get("description"),
                    "last_price": m.get("lastPrice"),
                    "change": m.get("netChange"),
                    "direction": "up" if (m.get("netChange") or 0) > 0 else "down",
                    "volume": m.get("volume"),
                    "total_volume": m.get("totalVolume"),
                }
                for m in screeners[:10]
            ],
        }

    return await cache_get_or_fetch(cache_key, _fetch, "quote")


async def get_market_hours(markets: list[str] | None = None) -> dict | None:
    if markets is None:
        markets = ["equity", "option"]

    data = await _schwab_get(
        "/markets",
        params={"markets": ",".join(markets)},
        service="marketdata",
        app_type=APP_MARKET,
    )
    if not isinstance(data, dict):
        return None

    formatted = {}
    for market_type, market_data in data.items():
        formatted[market_type] = {}
        for product, details in market_data.items():
            formatted[market_type][product] = {
                "date": details.get("date"),
                "product_name": details.get("productName"),
                "is_open": details.get("isOpen"),
                "session_hours": details.get("sessionHours", {}),
            }
    return formatted


async def get_accounts(include_positions: bool = True) -> list[dict] | None:
    params = {"fields": "positions"} if include_positions else None
    raw = await _schwab_get("/accounts", params=params, service="trader", app_type=APP_TRADER)
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("accounts") or [raw]
    return None


async def get_account_orders(account_number: str, max_results: int = 50) -> list[dict] | None:
    raw = await _schwab_get(
        f"/accounts/{account_number}/orders",
        params={"maxResults": max_results},
        service="trader",
        app_type=APP_TRADER,
    )
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("orders") or []
    return None


async def get_all_orders(max_results: int = 100) -> list[dict] | None:
    raw = await _schwab_get(
        "/orders",
        params={"maxResults": max_results},
        service="trader",
        app_type=APP_TRADER,
    )
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("orders") or []
    return None


async def get_account_transactions(account_number: str, max_results: int = 100) -> list[dict] | None:
    raw = await _schwab_get(
        f"/accounts/{account_number}/transactions",
        params={"maxResults": max_results},
        service="trader",
        app_type=APP_TRADER,
    )
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("transactions") or []
    return None


async def get_user_preferences() -> dict | None:
    raw = await _schwab_get("/userPreference", service="trader", app_type=APP_TRADER)
    if isinstance(raw, dict):
        return raw
    return None


async def preview_order(account_number: str, order_payload: dict) -> dict | None:
    raw = await _schwab_post(
        f"/accounts/{account_number}/previewOrder",
        payload=order_payload,
        service="trader",
        app_type=APP_TRADER,
    )
    if isinstance(raw, dict):
        return raw
    return None


async def place_order(account_number: str, order_payload: dict) -> dict | None:
    raw = await _schwab_post(
        f"/accounts/{account_number}/orders",
        payload=order_payload,
        service="trader",
        app_type=APP_TRADER,
        expected_status={httpx.codes.OK, httpx.codes.CREATED, httpx.codes.ACCEPTED},
    )
    if isinstance(raw, dict):
        return raw
    return None
