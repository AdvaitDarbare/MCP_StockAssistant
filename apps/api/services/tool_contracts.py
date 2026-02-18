"""Canonical tool contracts and output projection helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SCHWAB_MARKET_DATA_ENDPOINTS: list[dict[str, str]] = [
    {"method": "GET", "path": "/quotes", "summary": "Quotes by comma-separated symbols"},
    {"method": "GET", "path": "/{symbol_id}/quotes", "summary": "Quote for a single symbol"},
    {"method": "GET", "path": "/chains", "summary": "Option chain for a symbol"},
    {"method": "GET", "path": "/expirationchain", "summary": "Option expirations for a symbol"},
    {"method": "GET", "path": "/pricehistory", "summary": "OHLCV price history"},
    {"method": "GET", "path": "/movers/{symbol_id}", "summary": "Top movers for an index"},
    {"method": "GET", "path": "/markets", "summary": "Market hours for multiple markets"},
    {"method": "GET", "path": "/markets/{market_id}", "summary": "Market hours for one market"},
    {"method": "GET", "path": "/instruments", "summary": "Instrument lookup by symbols/projection"},
    {"method": "GET", "path": "/instruments/{cusip_id}", "summary": "Instrument lookup by CUSIP"},
]


SCHWAB_TRADER_ENDPOINTS: list[dict[str, str]] = [
    {"method": "GET", "path": "/accounts/{accountNumber}/orders", "summary": "Orders for one account"},
    {"method": "POST", "path": "/accounts/{accountNumber}/orders", "summary": "Place order"},
    {"method": "GET", "path": "/accounts/{accountNumber}/orders/{orderId}", "summary": "Order by ID"},
    {"method": "DELETE", "path": "/accounts/{accountNumber}/orders/{orderId}", "summary": "Cancel order"},
    {"method": "PUT", "path": "/accounts/{accountNumber}/orders/{orderId}", "summary": "Replace order"},
    {"method": "GET", "path": "/orders", "summary": "Orders for all accounts"},
    {"method": "POST", "path": "/accounts/{accountNumber}/previewOrder", "summary": "Preview order"},
    {"method": "GET", "path": "/accounts/{accountNumber}/transactions", "summary": "Transactions list"},
    {"method": "GET", "path": "/accounts/{accountNumber}/transactions/{transactionId}", "summary": "Transaction by ID"},
    {"method": "GET", "path": "/userPreference", "summary": "User preferences"},
]


TOOL_CONTRACTS: dict[str, dict[str, Any]] = {
    "get_quote": {
        "source": "schwab_market_data",
        "endpoint": "GET /quotes",
        "input": {"symbol": "string"},
        "output_fields": [
            "symbol",
            "price",
            "change",
            "percent_change",
            "volume",
            "open",
            "high",
            "low",
            "timestamp",
            "provider",
        ],
    },
    "get_historical_prices": {
        "source": "schwab_market_data",
        "endpoint": "GET /pricehistory",
        "input": {"symbol": "string", "days": "int"},
        "output_fields": ["symbol", "date", "open", "high", "low", "close", "volume"],
    },
    "get_company_profile": {
        "source": "finviz",
        "endpoint": "company profile scrape",
        "input": {"symbol": "string"},
        "output_fields": ["symbol", "company", "sector", "industry", "market_cap", "pe", "dividend_yield"],
    },
    "get_market_movers": {
        "source": "schwab_market_data",
        "endpoint": "GET /movers/{symbol_id}",
        "input": {},
        "output_fields": ["index", "sort", "movers[].symbol", "movers[].last_price", "movers[].change"],
    },
    "get_stock_news": {
        "source": "alpaca_news",
        "endpoint": "news endpoint",
        "input": {"symbol": "string|null", "limit": "int"},
        "output_fields": ["headline", "source", "url", "timestamp", "summary", "symbols"],
    },
    "get_market_hours": {
        "source": "schwab_market_data",
        "endpoint": "GET /markets",
        "input": {"markets": "list[str]|null"},
        "output_fields": ["market", "product", "is_open", "date", "session_hours"],
    },
    "get_company_overview": {
        "source": "finviz",
        "endpoint": "company overview scrape",
        "input": {"symbol": "string"},
        "output_fields": ["symbol", "company", "sector", "industry", "market_cap", "pe", "debt_eq", "target_price"],
    },
    "get_analyst_ratings": {
        "source": "finviz",
        "endpoint": "ratings scrape",
        "input": {"symbol": "string"},
        "output_fields": ["symbol", "ratings[].date", "ratings[].analyst", "ratings[].action", "ratings[].rating"],
    },
    "get_insider_trades": {
        "source": "finviz",
        "endpoint": "insider trades scrape",
        "input": {"symbol": "string", "limit": "int"},
        "output_fields": ["symbol", "insider_trades[].date", "insider_trades[].insider", "insider_trades[].transaction"],
    },
    "get_company_news": {
        "source": "finviz",
        "endpoint": "company news scrape",
        "input": {"symbol": "string", "limit": "int"},
        "output_fields": ["symbol", "news[].date", "news[].headline", "news[].source"],
    },
}


def list_tool_contracts() -> dict[str, Any]:
    return {
        "tools": deepcopy(TOOL_CONTRACTS),
        "schwab_market_data_endpoints": deepcopy(SCHWAB_MARKET_DATA_ENDPOINTS),
        "schwab_trader_endpoints": deepcopy(SCHWAB_TRADER_ENDPOINTS),
    }


def get_tool_contract(tool_name: str) -> dict[str, Any] | None:
    contract = TOOL_CONTRACTS.get((tool_name or "").strip())
    if not contract:
        return None
    return deepcopy(contract)


def _pick_fields(item: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {field: item.get(field) for field in fields if field in item}


def _project_market_hours(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    rows: list[dict[str, Any]] = []
    for market, products in raw.items():
        if not isinstance(products, dict):
            continue
        for product, detail in products.items():
            if not isinstance(detail, dict):
                continue
            rows.append(
                {
                    "market": market,
                    "product": product,
                    "is_open": detail.get("is_open"),
                    "date": detail.get("date"),
                    "session_hours": detail.get("session_hours"),
                }
            )
    return rows


def project_tool_output(tool_name: str, raw_output: Any) -> Any:
    tool = (tool_name or "").strip()
    if tool == "get_quote" and isinstance(raw_output, dict):
        return _pick_fields(
            raw_output,
            ["symbol", "price", "change", "percent_change", "volume", "open", "high", "low", "timestamp", "provider"],
        )
    if tool == "get_historical_prices" and isinstance(raw_output, list):
        rows = raw_output[-120:]
        return [_pick_fields(row, ["symbol", "date", "open", "high", "low", "close", "volume"]) for row in rows]
    if tool == "get_company_profile" and isinstance(raw_output, dict):
        return _pick_fields(raw_output, ["symbol", "company", "sector", "industry", "market_cap", "pe", "dividend_yield"])
    if tool == "get_market_movers" and isinstance(raw_output, dict):
        movers = raw_output.get("movers", [])
        slim = []
        if isinstance(movers, list):
            for row in movers[:10]:
                if isinstance(row, dict):
                    slim.append(_pick_fields(row, ["symbol", "last_price", "change", "direction", "total_volume"]))
        return {
            "index": raw_output.get("index"),
            "sort": raw_output.get("sort"),
            "movers": slim,
        }
    if tool == "get_stock_news" and isinstance(raw_output, list):
        slim = []
        for row in raw_output[:10]:
            if isinstance(row, dict):
                slim.append(_pick_fields(row, ["headline", "source", "url", "timestamp", "summary", "symbols"]))
        return slim
    if tool == "get_market_hours":
        return _project_market_hours(raw_output)
    if tool in {"get_company_overview", "get_analyst_ratings", "get_insider_trades", "get_company_news"}:
        return raw_output
    return raw_output


def build_structured_tool_payload(tool_name: str, tool_input: dict[str, Any], raw_output: Any) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "input": dict(tool_input or {}),
        "contract": get_tool_contract(tool_name),
        "output": project_tool_output(tool_name, raw_output),
        "raw": raw_output,
    }


def render_structured_market_tool_payload(payload: dict[str, Any]) -> str:
    tool = str(payload.get("tool", "")).strip()
    output = payload.get("output")

    if tool == "get_quote" and isinstance(output, dict):
        return (
            "Summary:\n"
            f"- {output.get('symbol', 'N/A')}: ${output.get('price', 'N/A')}\n"
            f"- Change: {output.get('change', 'N/A')} ({output.get('percent_change', 'N/A')}%)\n"
            f"- Volume: {output.get('volume', 'N/A')}\n"
            f"- Provider: {output.get('provider', 'N/A')}"
        )

    if tool == "get_historical_prices" and isinstance(output, list):
        if not output:
            return "Summary:\n- No historical price rows returned."
        first = output[0]
        last = output[-1]
        return (
            "Summary:\n"
            f"- Symbol: {last.get('symbol', 'N/A')}\n"
            f"- Window: {first.get('date', 'N/A')} to {last.get('date', 'N/A')}\n"
            f"- Start close: {first.get('close', 'N/A')}\n"
            f"- End close: {last.get('close', 'N/A')}\n"
            f"- Rows: {len(output)}"
        )

    if tool == "get_market_movers" and isinstance(output, dict):
        movers = output.get("movers", [])
        lines = [
            "Summary:",
            f"- Index: {output.get('index', 'N/A')}",
            f"- Sort: {output.get('sort', 'N/A')}",
            f"- Rows: {len(movers) if isinstance(movers, list) else 0}",
        ]
        if isinstance(movers, list):
            for row in movers[:5]:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- {row.get('symbol', 'N/A')}: {row.get('last_price', 'N/A')} ({row.get('change', 'N/A')})"
                )
        return "\n".join(lines)

    if tool == "get_stock_news" and isinstance(output, list):
        if not output:
            return "Summary:\n- No news rows returned."
        lines = ["Summary:", f"- News rows: {len(output)}"]
        for row in output[:5]:
            if not isinstance(row, dict):
                continue
            lines.append(f"- {row.get('source', 'N/A')}: {row.get('headline', 'N/A')}")
        return "\n".join(lines)

    if tool == "get_market_hours" and isinstance(output, list):
        if not output:
            return "Summary:\n- No market-hours rows returned."
        lines = ["Summary:", f"- Market-hour rows: {len(output)}"]
        for row in output[:5]:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"- {row.get('market', 'N/A')}/{row.get('product', 'N/A')}: is_open={row.get('is_open', 'N/A')}"
            )
        return "\n".join(lines)

    if tool == "get_company_profile" and isinstance(output, dict):
        return (
            "Summary:\n"
            f"- {output.get('symbol', 'N/A')} | {output.get('company', 'N/A')}\n"
            f"- Sector: {output.get('sector', 'N/A')}\n"
            f"- Industry: {output.get('industry', 'N/A')}\n"
            f"- Market Cap: {output.get('market_cap', 'N/A')}"
        )

    return str(output) if output is not None else "No tool output."
