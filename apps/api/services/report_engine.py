"""Report engine for advanced stock/portfolio workflows."""

from __future__ import annotations

import asyncio
import math
import statistics
from datetime import datetime, timezone
from typing import Any

from apps.api.db import portfolio_repo
from apps.api.db.report_repo import save_report_run
from apps.api.config import settings
from apps.api.services.finviz_client import (
    get_analyst_ratings,
    get_company_news,
    get_company_overview,
    get_insider_trades,
)
from apps.api.services.fred_client import get_key_indicators
from apps.api.services.market_data_provider import (
    get_unified_history,
    get_unified_market_movers,
    get_unified_quote,
)
from apps.api.services.tavily_client import get_news_sentiment, search_financial_news
from apps.api.services.report_prompts import PROMPT_TEMPLATES
from apps.api.agents.technical_analysis.tools import analyze_technicals


DEV_PORTFOLIO_ID = settings.DEV_PORTFOLIO_ID

DEFAULT_SCREEN_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "JPM", "V",
    "MA", "UNH", "XOM", "LLY", "HD", "COST", "ABBV", "PFE", "KO", "PEP", "PG",
    "MRK", "CSCO", "ORCL", "CRM", "AMD", "NFLX", "INTU", "ADBE", "TXN",
]

DEFAULT_DIVIDEND_UNIVERSE = [
    "JNJ", "PG", "KO", "PEP", "ABBV", "XOM", "CVX", "T", "VZ", "IBM",
    "MMM", "MCD", "MO", "PM", "HD", "LOW", "DUK", "SO", "NEE", "BMY",
]

SECTOR_COMPETITORS = {
    "semiconductors": ["NVDA", "AMD", "AVGO", "QCOM", "INTC", "TXN"],
    "ai infrastructure": ["NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD"],
    "big tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"],
    "banking": ["JPM", "BAC", "WFC", "C", "GS", "MS"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PSX"],
    "healthcare": ["LLY", "JNJ", "PFE", "MRK", "ABBV", "BMY"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"N/A", "-", "--", "None", "."}:
        return None
    text = text.replace(",", "").replace("$", "")
    suffix = 1.0
    if text.endswith("%"):
        text = text[:-1]
    if text.endswith("T"):
        suffix = 1_000_000_000_000
        text = text[:-1]
    elif text.endswith("B"):
        suffix = 1_000_000_000
        text = text[:-1]
    elif text.endswith("M"):
        suffix = 1_000_000
        text = text[:-1]
    elif text.endswith("K"):
        suffix = 1_000
        text = text[:-1]
    try:
        return float(text) * suffix
    except ValueError:
        return None


def _safe_pct(value: Any) -> float | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    if parsed > 1 and parsed <= 100:
        return parsed / 100
    if parsed > 100:
        return parsed / 10000
    return parsed


def _fmt_num(value: Any, ndigits: int = 2) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.{ndigits}f}"
    except Exception:
        return str(value)


def _fmt_pct(value: Any, ndigits: int = 1) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.{ndigits}f}%"
    except Exception:
        return str(value)


def _to_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "No rows."
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join([head, sep] + body)


def _daily_returns(history: list[dict[str, Any]]) -> list[float]:
    closes = [float(x["close"]) for x in history if x.get("close") is not None]
    if len(closes) < 2:
        return []
    returns = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev <= 0:
            continue
        returns.append((closes[i] / prev) - 1)
    return returns


def _correlation(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 3:
        return None
    a2 = a[-n:]
    b2 = b[-n:]
    mean_a = statistics.mean(a2)
    mean_b = statistics.mean(b2)
    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(a2, b2))
    den_a = math.sqrt(sum((x - mean_a) ** 2 for x in a2))
    den_b = math.sqrt(sum((y - mean_b) ** 2 for y in b2))
    if den_a == 0 or den_b == 0:
        return None
    return num / (den_a * den_b)


def _extract_ticker(payload: dict[str, Any]) -> str | None:
    for key in ("ticker", "symbol"):
        if payload.get(key):
            return str(payload[key]).upper()
    stock = payload.get("stock") or payload.get("company")
    if isinstance(stock, str):
        token = stock.strip().split()[0].upper()
        if 1 <= len(token) <= 6 and token.isalpha():
            return token
    return None


def _extract_top_headlines(fin_news: dict[str, Any] | None, web_news: dict[str, Any] | None, limit: int = 4) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in (fin_news or {}).get("news", [])[:limit]:
        out.append(
            {
                "title": str(item.get("headline", "")),
                "source": str(item.get("source", "Finviz")),
                "url": str(item.get("link", "")),
            }
        )
    if len(out) < limit:
        for item in (web_news or {}).get("results", [])[:limit]:
            if len(out) >= limit:
                break
            out.append(
                {
                    "title": str(item.get("title", "")),
                    "source": "Web",
                    "url": str(item.get("url", "")),
                }
            )
    return out


async def _run_research_subagents(symbol: str, include_macro: bool = False) -> dict[str, Any]:
    """Run lightweight specialist collectors in parallel (sub-agent pattern)."""
    tasks: dict[str, Any] = {
        "fundamentals": get_company_overview(symbol),
        "market_quote": get_unified_quote(symbol),
        "market_history": get_unified_history(symbol, days=365),
        "analyst_ratings": get_analyst_ratings(symbol),
        "company_news": get_company_news(symbol, limit=12),
        "insider_trades": get_insider_trades(symbol, limit=12),
        "web_sentiment": get_news_sentiment(symbol),
        "web_news": search_financial_news(f"{symbol} stock outlook", limit=5),
    }
    if include_macro:
        tasks["macro"] = get_key_indicators()

    names = list(tasks.keys())
    try:
        # Wrap gather in a timeout to prevent hanging on slow scrapers (Finviz, etc.)
        values = await asyncio.wait_for(asyncio.gather(*tasks.values(), return_exceptions=True), timeout=25.0)
    except asyncio.TimeoutError:
        # If the whole gather times out, return what we have (empty or errors)
        return {"subagent_trace": [{"agent": n, "status": "timeout"} for n in names]}

    out: dict[str, Any] = {}
    for name, value in zip(names, values):
        if isinstance(value, Exception):
            print(f"Subagent {name} failed: {value}")
            out[name] = None
        else:
            out[name] = value

    out["subagent_trace"] = [
        {"agent": name, "status": "ok" if out.get(name) else "empty"}
        for name in names
    ]
    return out


async def _load_stock_context(symbol: str) -> dict[str, Any]:
    subagent_outputs = await _run_research_subagents(symbol, include_macro=False)
    overview = subagent_outputs.get("fundamentals")
    quote = subagent_outputs.get("market_quote")
    history = subagent_outputs.get("market_history")
    ratings = subagent_outputs.get("analyst_ratings")
    news = subagent_outputs.get("company_news")
    insiders = subagent_outputs.get("insider_trades")
    web_sentiment = subagent_outputs.get("web_sentiment")
    web_news = subagent_outputs.get("web_news")
    return {
        "symbol": symbol.upper(),
        "overview": overview or {},
        "quote": quote or {},
        "history": history or [],
        "ratings": ratings or {},
        "news": news or {},
        "insiders": insiders or {},
        "web_sentiment": web_sentiment or {},
        "web_news": web_news or {},
        "headlines": _extract_top_headlines(news or {}, web_news or {}),
        "subagent_trace": subagent_outputs.get("subagent_trace", []),
    }


def _moat_rating(overview: dict[str, Any]) -> str:
    roe = _safe_pct(overview.get("roe")) or 0
    margin = _safe_pct(overview.get("profit_margin")) or 0
    debt = _safe_float(overview.get("debt_eq")) or 0
    score = (roe * 100) + (margin * 100) - min(debt, 200) * 0.05
    if score >= 30:
        return "strong"
    if score >= 15:
        return "moderate"
    return "weak"


def _risk_score(overview: dict[str, Any], quote: dict[str, Any]) -> tuple[int, str]:
    beta = _safe_float(overview.get("beta")) or 1.0
    debt = _safe_float(overview.get("debt_eq")) or 0
    pe = _safe_float(overview.get("pe")) or 20
    pct = abs(float(quote.get("percent_change") or 0))
    score = 3 + min(beta, 3) + min(debt / 150, 2) + min(pe / 40, 2) + min(pct / 5, 1)
    score_int = max(1, min(10, int(round(score))))
    reason = f"beta={beta:.2f}, debt/equity={debt:.2f}, P/E={pe:.1f}, daily move={pct:.2f}%"
    return score_int, reason


async def build_goldman_screener(payload: dict[str, Any]) -> dict[str, Any]:
    profile = payload.get("investment_profile", {})
    universe = payload.get("universe") or DEFAULT_SCREEN_UNIVERSE
    limit = min(int(payload.get("limit", 10)), 20)

    tasks = [get_company_overview(sym) for sym in universe]
    overviews = await asyncio.gather(*tasks, return_exceptions=True)

    # Pre-fetch all quotes in a single batch call to avoid N+1 sequential requests (Q-1)
    quotes_map = await get_unified_quotes(universe)

    picks = []
    for symbol, overview_raw in zip(universe, overviews):
        if isinstance(overview_raw, Exception) or not overview_raw:
            continue
        overview = overview_raw
        quote = quotes_map.get(symbol.upper()) or {}
        price = quote.get("price")
        pe = _safe_float(overview.get("pe"))
        debt = _safe_float(overview.get("debt_eq"))
        div_yield = _safe_pct(overview.get("dividend_yield"))
        sales_5y = _safe_pct(overview.get("sales_past_5y"))
        payout = _safe_pct(overview.get("payout_ratio"))
        moat = _moat_rating(overview)
        risk, risk_reason = _risk_score(overview, quote)

        if pe is None or price is None:
            continue
        sector = overview.get("sector") or "Unknown"
        score = (
            (0 if pe > 40 else (40 - pe) * 0.5)
            + ((sales_5y or 0) * 150)
            + (10 if moat == "strong" else 5 if moat == "moderate" else 0)
            + (5 if (div_yield or 0) > 0.01 and (payout or 0) < 0.7 else 0)
            - (risk * 1.2)
        )

        bull_target = price * 1.2
        bear_target = price * 0.85
        entry_low = price * 0.96
        entry_high = price * 1.01
        stop = price * 0.9

        picks.append(
            {
                "symbol": symbol.upper(),
                "sector": sector,
                "price": price,
                "pe": pe,
                "sector_pe_comparison": "Below sector avg" if pe < 25 else "Above sector avg",
                "revenue_growth_5y": sales_5y,
                "debt_to_equity": debt,
                "dividend_yield": div_yield,
                "payout_ratio": payout,
                "moat": moat,
                "bull_target_12m": bull_target,
                "bear_target_12m": bear_target,
                "risk_rating": risk,
                "risk_reason": risk_reason,
                "entry_zone": [entry_low, entry_high],
                "stop_loss": stop,
                "score": round(score, 2),
                "news_sentiment": "N/A",
            }
        )

    ranked = sorted(picks, key=lambda x: x["score"], reverse=True)[:limit]
    if ranked:
        sentiment_tasks = [get_news_sentiment(p["symbol"]) for p in ranked]
        sentiments = await asyncio.gather(*sentiment_tasks, return_exceptions=True)
        for pick, sentiment in zip(ranked, sentiments):
            if isinstance(sentiment, Exception) or not sentiment:
                continue
            pick["news_sentiment"] = sentiment.get("news_sentiment", "N/A")

    table_rows = [
        [
            p["symbol"],
            p["sector"],
            f"${_fmt_num(p['price'])}",
            _fmt_num(p["pe"], 1),
            _fmt_pct(p["revenue_growth_5y"]),
            _fmt_num(p["debt_to_equity"], 2),
            _fmt_pct(p["dividend_yield"]),
            p["moat"],
            p.get("news_sentiment", "N/A"),
            p["risk_rating"],
            f"${_fmt_num(p['bull_target_12m'])} / ${_fmt_num(p['bear_target_12m'])}",
        ]
        for p in ranked
    ]
    markdown = "\n".join(
        [
            "# Goldman Sachs Style Screening Report",
            "",
            f"Generated: {_now_iso()}",
            f"Profile snapshot: {profile}",
            "",
            _to_markdown_table(
                [
                    "Ticker",
                    "Sector",
                    "Price",
                    "P/E",
                    "Rev 5Y",
                    "D/E",
                    "Div Yield",
                    "Moat",
                    "News Sent.",
                    "Risk(1-10)",
                    "Bull/Bear 12M",
                ],
                table_rows,
            ),
        ]
    )
    return {
        "report_type": "goldman_screener",
        "title": "Goldman Sachs Stock Screener",
        "generated_at": _now_iso(),
        "data": {"picks": ranked},
        "markdown": markdown,
        "assumptions": [
            "Sector-average P/E comparison uses generic benchmark when sector-specific average unavailable.",
            "Price targets and entry zones are model-derived bands, not analyst consensus.",
        ],
        "limitations": [
            "Revenue growth and payout metrics depend on Finviz field availability per ticker.",
        ],
        "sources_used": ["market_data_provider", "finviz", "tavily_news_sentiment"],
    }


async def build_morgan_dcf(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = _extract_ticker(payload)
    if not ticker:
        raise ValueError("Ticker is required for DCF report.")

    ctx = await _load_stock_context(ticker)
    overview = ctx["overview"]
    quote = ctx["quote"]
    current_price = float(quote.get("price") or 0)
    market_cap = _safe_float(overview.get("market_cap")) or (current_price * 1_000_000_000)

    revenue_base = _safe_float(overview.get("revenue")) or max(market_cap * 0.25, 1_000_000_000)
    sales_growth = _safe_pct(overview.get("sales_past_5y")) or _safe_pct(overview.get("eps_next_y")) or 0.08
    op_margin = _safe_pct(overview.get("oper_margin")) or 0.2
    beta = _safe_float(overview.get("beta")) or 1.0

    macro = await get_key_indicators()
    rf = ((macro.get("10y_treasury") or {}).get("value") or 4.0) / 100
    equity_risk_premium = 0.05
    wacc = min(0.16, max(0.07, rf + beta * equity_risk_premium))
    terminal_growth = min(0.03, max(0.02, (macro.get("gdp") or {}).get("value", 2.0) / 1000))

    projections = []
    revenue = revenue_base
    for year in range(1, 6):
        growth = max(0.02, sales_growth - (year - 1) * 0.01)
        revenue = revenue * (1 + growth)
        ebit = revenue * op_margin
        nopat = ebit * (1 - 0.21)
        reinvestment = nopat * 0.35
        fcf = nopat - reinvestment
        discount = (1 + wacc) ** year
        pv = fcf / discount
        projections.append(
            {
                "year": year,
                "growth": growth,
                "revenue": revenue,
                "op_margin": op_margin,
                "fcf": fcf,
                "pv_fcf": pv,
            }
        )

    fcf5 = projections[-1]["fcf"]
    terminal_perpetuity = (fcf5 * (1 + terminal_growth)) / (wacc - terminal_growth)
    exit_multiple = 14.0
    terminal_exit = (projections[-1]["revenue"] * op_margin) * exit_multiple
    pv_terminal_perpetuity = terminal_perpetuity / ((1 + wacc) ** 5)
    pv_terminal_exit = terminal_exit / ((1 + wacc) ** 5)
    enterprise_value = sum(p["pv_fcf"] for p in projections) + (pv_terminal_perpetuity + pv_terminal_exit) / 2

    sensitivity = []
    for dr in [wacc - 0.01, wacc, wacc + 0.01]:
        for tg in [terminal_growth - 0.005, terminal_growth, terminal_growth + 0.005]:
            if dr <= tg:
                continue
            tv = (fcf5 * (1 + tg)) / (dr - tg)
            ev = sum(p["fcf"] / ((1 + dr) ** p["year"]) for p in projections) + (tv / ((1 + dr) ** 5))
            sensitivity.append({"discount_rate": dr, "terminal_growth": tg, "fair_value": ev})

    verdict = "fairly valued"
    if enterprise_value > market_cap * 1.1:
        verdict = "undervalued"
    elif enterprise_value < market_cap * 0.9:
        verdict = "overvalued"

    projection_table = _to_markdown_table(
        ["Year", "Revenue", "Growth", "Op Margin", "FCF", "PV FCF"],
        [
            [
                p["year"],
                _fmt_num(p["revenue"], 0),
                _fmt_pct(p["growth"]),
                _fmt_pct(p["op_margin"]),
                _fmt_num(p["fcf"], 0),
                _fmt_num(p["pv_fcf"], 0),
            ]
            for p in projections
        ],
    )
    sensitivity_table = _to_markdown_table(
        ["Discount Rate", "Terminal Growth", "Fair Value (EV)"],
        [[_fmt_pct(s["discount_rate"]), _fmt_pct(s["terminal_growth"]), _fmt_num(s["fair_value"], 0)] for s in sensitivity[:9]],
    )
    markdown = "\n".join(
        [
            f"# Morgan Stanley DCF Memo: {ticker}",
            "",
            f"Current market cap (proxy): ${_fmt_num(market_cap, 0)}",
            f"Model EV: ${_fmt_num(enterprise_value, 0)}",
            f"Verdict: **{verdict.upper()}**",
            "",
            "## 5-Year Projection",
            projection_table,
            "",
            "## Sensitivity",
            sensitivity_table,
            "",
            "## Recent Catalysts",
            _to_markdown_table(
                ["Headline", "Source"],
                [[h.get("title", "N/A"), h.get("source", "N/A")] for h in ctx.get("headlines", [])[:4]] or [["N/A", "N/A"]],
            ),
        ]
    )
    return {
        "report_type": "morgan_dcf",
        "title": "Morgan Stanley DCF Valuation",
        "generated_at": _now_iso(),
        "data": {
            "ticker": ticker,
            "wacc": wacc,
            "terminal_growth": terminal_growth,
            "enterprise_value": enterprise_value,
            "market_cap_proxy": market_cap,
            "verdict": verdict,
            "projections": projections,
            "sensitivity": sensitivity,
            "subagent_trace": ctx.get("subagent_trace", []),
        },
        "markdown": markdown,
        "assumptions": [
            "FCF derived from operating margin and a fixed reinvestment ratio.",
            "Market cap and revenue may be proxy-derived when fields are missing.",
        ],
        "limitations": [
            "Share-count-level intrinsic value per share is not computed without a reliable share count source.",
        ],
        "sources_used": ["market_data_provider", "finviz", "fred", "tavily_financial_news"],
    }


async def _resolve_portfolio_input(payload: dict[str, Any]) -> list[dict[str, Any]]:
    holdings = payload.get("holdings")
    if isinstance(holdings, list) and holdings:
        normalized = []
        total_weight = 0.0
        for h in holdings:
            symbol = str(h.get("symbol", "")).upper()
            if not symbol:
                continue
            weight = float(h.get("weight", 0))
            total_weight += max(weight, 0)
            normalized.append({"symbol": symbol, "weight": max(weight, 0)})
        if total_weight > 0:
            for h in normalized:
                h["weight"] = h["weight"] / total_weight
        elif normalized:
            equal = 1 / len(normalized)
            for h in normalized:
                h["weight"] = equal
        return normalized

    db_holdings = await portfolio_repo.get_holdings(DEV_PORTFOLIO_ID)
    if not db_holdings:
        return []
    total_cost = sum(float(h["shares"]) * float(h["avg_cost"]) for h in db_holdings)
    if total_cost <= 0:
        eq = 1 / len(db_holdings)
        return [{"symbol": h["symbol"], "weight": eq} for h in db_holdings]
    return [
        {
            "symbol": h["symbol"],
            "weight": (float(h["shares"]) * float(h["avg_cost"])) / total_cost,
        }
        for h in db_holdings
    ]


async def build_bridgewater_risk(payload: dict[str, Any]) -> dict[str, Any]:
    positions = await _resolve_portfolio_input(payload)
    if not positions:
        raise ValueError("Portfolio holdings are required for risk assessment.")

    symbols = [p["symbol"] for p in positions]
    histories = await asyncio.gather(*[get_unified_history(sym, days=260) for sym in symbols])
    returns_map = {sym: _daily_returns(hist) for sym, hist in zip(symbols, histories)}

    corr_rows = []
    for s1 in symbols:
        row = {"symbol": s1}
        for s2 in symbols:
            c = _correlation(returns_map.get(s1, []), returns_map.get(s2, []))
            row[s2] = c
        corr_rows.append(row)

    overviews = await asyncio.gather(*[get_company_overview(sym) for sym in symbols])
    sector_exposure: dict[str, float] = {}
    geo_exposure: dict[str, float] = {}
    for p, ov in zip(positions, overviews):
        ov = ov or {}
        sector = ov.get("sector") or "Unknown"
        country = ov.get("country") or "US"
        sector_exposure[sector] = sector_exposure.get(sector, 0.0) + p["weight"]
        geo_exposure[country] = geo_exposure.get(country, 0.0) + p["weight"]

    concentration = sorted(sector_exposure.items(), key=lambda x: x[1], reverse=True)
    concentration_risk = concentration[0][1] if concentration else 0
    recession_drawdown = -(
        0.12 + concentration_risk * 0.18 + (sum(abs(statistics.mean(v)) for v in returns_map.values() if v) * 5)
    )

    top_risks = [
        {"risk": "Sector concentration", "severity": round(concentration_risk * 100, 1)},
        {"risk": "Correlation clustering", "severity": round(max([abs(r[symbols[0]] or 0) for r in corr_rows[1:]] + [0]) * 100, 1)},
        {"risk": "Liquidity + single-name", "severity": round(max(p["weight"] for p in positions) * 100, 1)},
    ]

    heatmap_rows = [[k, _fmt_pct(v)] for k, v in concentration]
    markdown = "\n".join(
        [
            "# Bridgewater Portfolio Risk Report",
            "",
            f"Estimated recession stress drawdown: **{recession_drawdown*100:.1f}%**",
            "",
            "## Sector Heatmap Summary",
            _to_markdown_table(["Sector", "Weight"], heatmap_rows),
        ]
    )
    return {
        "report_type": "bridgewater_risk",
        "title": "Bridgewater Risk Assessment",
        "generated_at": _now_iso(),
        "data": {
            "positions": positions,
            "sector_exposure": sector_exposure,
            "geo_exposure": geo_exposure,
            "correlation_matrix": corr_rows,
            "estimated_recession_drawdown": recession_drawdown,
            "top_risks": top_risks,
            "hedging_strategies": [
                "Add index put spread protection on the largest equity sleeve.",
                "Reduce top sector exposure and rotate 10-15% into short-duration Treasuries.",
                "Cap single-stock allocations at 8% and rebalance monthly.",
            ],
        },
        "markdown": markdown,
        "assumptions": [
            "Risk model is based on trailing returns and static weights.",
        ],
        "limitations": [
            "No intraday liquidity/volume shock model is included.",
        ],
    }


async def build_jpm_earnings(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = _extract_ticker(payload)
    if not ticker:
        raise ValueError("Ticker is required for earnings analysis.")

    ctx = await _load_stock_context(ticker)
    quote = ctx["quote"]
    overview = ctx["overview"]
    history = ctx["history"]
    news = (ctx["news"] or {}).get("news", [])
    ratings = (ctx["ratings"] or {}).get("ratings", [])
    web_sent = ctx.get("web_sentiment", {})

    beat_miss = []
    for n in news[:10]:
        title = str(n.get("headline", "")).lower()
        if "beat" in title:
            beat_miss.append("beat")
        elif "miss" in title:
            beat_miss.append("miss")
    beat_count = beat_miss.count("beat")
    miss_count = beat_miss.count("miss")

    returns = _daily_returns(history)
    vol = statistics.pstdev(returns) if len(returns) > 10 else 0.02
    implied_move_proxy = (quote.get("price") or 0) * vol * 1.5
    current_price = float(quote.get("price") or 0)
    bullish = (beat_count >= miss_count) and ((_safe_pct(overview.get("eps_next_y")) or 0) > 0)
    recommended_play = "wait"
    if bullish and (_safe_float(quote.get("percent_change")) or 0) > -2:
        recommended_play = "buy before"
    elif not bullish:
        recommended_play = "sell before"

    markdown = "\n".join(
        [
            f"# JPMorgan Pre-Earnings Brief: {ticker}",
            "",
            f"Decision summary: **{recommended_play.upper()}**",
            f"Implied move proxy (1-day): **${_fmt_num(implied_move_proxy)}**",
            "",
            _to_markdown_table(
                ["Metric", "Value"],
                [
                    ["Beat/Miss signal from recent headlines", f"{beat_count} beats / {miss_count} misses"],
                    ["Consensus EPS proxy (next Y field)", overview.get("eps_next_y", "N/A")],
                    ["News sentiment", web_sent.get("news_sentiment", "N/A")],
                    ["Current Price", f"${_fmt_num(current_price)}"],
                    ["Bull case target (+8%)", f"${_fmt_num(current_price * 1.08)}"],
                    ["Bear case target (-10%)", f"${_fmt_num(current_price * 0.90)}"],
                ],
            ),
            "",
            "## Headlines In Focus",
            _to_markdown_table(
                ["Headline", "Source"],
                [[h.get("title", "N/A"), h.get("source", "N/A")] for h in ctx.get("headlines", [])[:4]] or [["N/A", "N/A"]],
            ),
        ]
    )
    return {
        "report_type": "jpm_earnings",
        "title": "JPMorgan Earnings Analyzer",
        "generated_at": _now_iso(),
        "data": {
            "ticker": ticker,
            "recent_beat_count": beat_count,
            "recent_miss_count": miss_count,
            "consensus_eps_proxy": overview.get("eps_next_y"),
            "implied_move_proxy": implied_move_proxy,
            "historical_reaction_proxy": vol,
            "recommended_play": recommended_play,
            "ratings_sample": ratings[:4],
            "headlines": ctx.get("headlines", [])[:6],
            "news_sentiment": web_sent,
            "subagent_trace": ctx.get("subagent_trace", []),
        },
        "markdown": markdown,
        "assumptions": [
            "Earnings beat/miss history is inferred from headline text when official estimate history is unavailable.",
        ],
        "limitations": [
            "Options-implied move is a volatility proxy, not live options-chain IV.",
        ],
        "sources_used": ["market_data_provider", "finviz", "tavily_news_sentiment", "tavily_financial_news"],
    }


async def build_blackrock_builder(payload: dict[str, Any]) -> dict[str, Any]:
    details = payload.get("details", payload)
    risk = str(details.get("risk_tolerance", "moderate")).lower()
    account_type = str(details.get("account_type", "taxable")).lower()
    monthly = float(details.get("monthly_investment", 0) or 0)

    if risk in {"aggressive", "high"}:
        alloc = {"stocks": 0.80, "bonds": 0.15, "alternatives": 0.05}
    elif risk in {"conservative", "low"}:
        alloc = {"stocks": 0.45, "bonds": 0.50, "alternatives": 0.05}
    else:
        alloc = {"stocks": 0.65, "bonds": 0.30, "alternatives": 0.05}

    etfs = {
        "stocks_core": ["VTI", "VOO", "QQQM"],
        "stocks_satellite": ["SMH", "VIG", "XLF"],
        "bonds_core": ["BND", "AGG", "SCHP"],
        "alternatives": ["GLD", "VNQ"],
    }
    exp_return = alloc["stocks"] * 0.09 + alloc["bonds"] * 0.04 + alloc["alternatives"] * 0.05
    max_drawdown = -(alloc["stocks"] * 0.42 + alloc["bonds"] * 0.08 + alloc["alternatives"] * 0.15)

    markdown = "\n".join(
        [
            "# BlackRock Portfolio Builder",
            "",
            _to_markdown_table(
                ["Asset Class", "Allocation", "Suggested ETFs/Funds"],
                [
                    ["Stocks (Core+Satellite)", _fmt_pct(alloc["stocks"]), ", ".join(etfs["stocks_core"] + etfs["stocks_satellite"][:1])],
                    ["Bonds", _fmt_pct(alloc["bonds"]), ", ".join(etfs["bonds_core"][:2])],
                    ["Alternatives", _fmt_pct(alloc["alternatives"]), ", ".join(etfs["alternatives"])],
                ],
            ),
            "",
            f"Expected annual return range: **{(exp_return-0.02)*100:.1f}% - {(exp_return+0.02)*100:.1f}%**",
            f"Expected bad-year drawdown: **{max_drawdown*100:.1f}%**",
            "Rebalancing: quarterly check, trade only if sleeve drift exceeds +/-5%.",
            f"Tax efficiency note ({account_type}): prioritize low-turnover broad-market ETFs in taxable accounts.",
            f"DCA plan: invest ${monthly:,.0f}/month proportionally to target weights.",
            "Benchmark: 70/30 blend of S&P 500 and US Aggregate Bond Index.",
        ]
    )
    return {
        "report_type": "blackrock_builder",
        "title": "BlackRock Portfolio Builder",
        "generated_at": _now_iso(),
        "data": {
            "allocation": alloc,
            "etf_recommendations": etfs,
            "expected_return": exp_return,
            "expected_max_drawdown": max_drawdown,
            "benchmark": "70% S&P 500 / 30% Bloomberg US Agg",
        },
        "markdown": markdown,
        "assumptions": ["Expected returns are long-horizon historical proxies."],
        "limitations": ["Does not include personal tax-lot constraints or employer plan fund menus."],
    }


async def build_citadel_technical(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = _extract_ticker(payload)
    if not ticker:
        raise ValueError("Ticker is required for technical analysis.")

    history = await get_unified_history(ticker, days=420)
    indicators = await analyze_technicals.ainvoke({"symbol": ticker, "price_data": history}) or {}
    if not history:
        raise ValueError(f"No price history available for {ticker}.")

    closes = [float(x["close"]) for x in history if x.get("close") is not None]
    current = closes[-1]
    high = max(closes[-120:])
    low = min(closes[-120:])
    diff = high - low
    fib_levels = {
        "23.6%": high - diff * 0.236,
        "38.2%": high - diff * 0.382,
        "50.0%": high - diff * 0.5,
        "61.8%": high - diff * 0.618,
    }

    support = indicators.get("support") or min(closes[-20:])
    resistance = indicators.get("resistance") or max(closes[-20:])
    stop = support * 0.98
    target = resistance * 1.05
    rr = (target - current) / max(current - stop, 0.0001)

    confidence = "neutral"
    if indicators.get("trend") == "bullish" and (indicators.get("rsi_14") or 50) < 70 and rr >= 1.5:
        confidence = "buy"
    elif indicators.get("trend") == "bearish" and (indicators.get("rsi_14") or 50) > 30:
        confidence = "sell"

    markdown = "\n".join(
        [
            f"# Citadel Technical Report Card: {ticker}",
            "",
            _to_markdown_table(
                ["Metric", "Reading"],
                [
                    ["Trend", indicators.get("trend", "N/A")],
                    ["RSI(14)", indicators.get("rsi_14", "N/A")],
                    ["MACD", indicators.get("macd", "N/A")],
                    ["SMA 50 / SMA 200", f"{indicators.get('sma_50', 'N/A')} / {indicators.get('sma_200', 'N/A')}"],
                    ["Support / Resistance", f"${_fmt_num(support)} / ${_fmt_num(resistance)}"],
                    ["Entry / Stop / Target", f"${_fmt_num(current)} / ${_fmt_num(stop)} / ${_fmt_num(target)}"],
                    ["Risk:Reward", f"{rr:.2f}x"],
                    ["Confidence", confidence.upper()],
                ],
            ),
            "",
            "Fibonacci retracement levels:",
            _to_markdown_table(["Level", "Price"], [[k, f"${_fmt_num(v)}"] for k, v in fib_levels.items()]),
        ]
    )
    return {
        "report_type": "citadel_technical",
        "title": "Citadel Technical Analysis",
        "generated_at": _now_iso(),
        "data": {
            "ticker": ticker,
            "trend": indicators.get("trend"),
            "support": support,
            "resistance": resistance,
            "entry": current,
            "stop_loss": stop,
            "target": target,
            "risk_reward": rr,
            "fib_levels": fib_levels,
            "confidence": confidence,
            "indicators": indicators,
        },
        "markdown": markdown,
        "assumptions": ["Multi-timeframe trend is inferred from daily data history and moving averages."],
        "limitations": ["Pattern recognition is rule-based and does not include image-based chart model inference."],
    }


async def build_harvard_dividend(payload: dict[str, Any]) -> dict[str, Any]:
    amount = float(payload.get("investment_amount", 100000) or 100000)
    account_type = str(payload.get("account_type", "taxable"))
    universe = payload.get("universe") or DEFAULT_DIVIDEND_UNIVERSE

    overviews = await asyncio.gather(*[get_company_overview(sym) for sym in universe], return_exceptions=True)
    picks = []
    for sym, ov_raw in zip(universe, overviews):
        if isinstance(ov_raw, Exception) or not ov_raw:
            continue
        ov = ov_raw
        dy = _safe_pct(ov.get("dividend_yield")) or 0
        payout = _safe_pct(ov.get("payout_ratio")) or 0.5
        debt = _safe_float(ov.get("debt_eq")) or 80
        beta = _safe_float(ov.get("beta")) or 1.0
        growth = _safe_pct(ov.get("sales_past_5y")) or 0.04
        safety = max(1, min(10, int(round(9 - payout * 6 - debt / 120 - max(0, beta - 1) * 2 + growth * 10))))
        picks.append(
            {
                "symbol": sym,
                "yield": dy,
                "payout": payout,
                "debt_eq": debt,
                "dividend_growth_5y": growth,
                "safety_score": safety,
                "years_growth_proxy": int(max(1, growth * 100)),
            }
        )

    ranked = sorted(picks, key=lambda x: (x["safety_score"], x["yield"]), reverse=True)[:20]
    avg_yield = statistics.mean([p["yield"] for p in ranked]) if ranked else 0
    monthly_income = amount * avg_yield / 12
    div_growth = max(0.02, statistics.mean([p["dividend_growth_5y"] for p in ranked]) if ranked else 0.04)
    drip_10y = amount * ((1 + avg_yield + div_growth) ** 10)

    markdown = "\n".join(
        [
            "# Harvard Endowment Dividend Blueprint",
            "",
            _to_markdown_table(
                ["Ticker", "Yield", "Safety (1-10)", "Payout", "Debt/Eq", "5Y Growth Proxy"],
                [
                    [
                        p["symbol"],
                        _fmt_pct(p["yield"]),
                        p["safety_score"],
                        _fmt_pct(p["payout"]),
                        _fmt_num(p["debt_eq"], 1),
                        _fmt_pct(p["dividend_growth_5y"]),
                    ]
                    for p in ranked
                ],
            ),
            "",
            f"Monthly income projection: **${monthly_income:,.2f}**",
            f"DRIP projection (10Y): **${drip_10y:,.0f}**",
            f"Tax note ({account_type}): qualified dividends may receive favorable federal tax rates in taxable accounts.",
        ]
    )
    return {
        "report_type": "harvard_dividend",
        "title": "Harvard Endowment Dividend Strategy",
        "generated_at": _now_iso(),
        "data": {
            "picks": ranked,
            "monthly_income_projection": monthly_income,
            "drip_projection_10y": drip_10y,
            "avg_yield": avg_yield,
            "dividend_growth_rate_estimate": div_growth,
        },
        "markdown": markdown,
        "assumptions": ["Dividend safety model uses payout, leverage, beta, and growth proxies."],
        "limitations": ["Dividend streak years may be approximate if explicit history is unavailable from source."],
    }


async def build_bain_competitive(payload: dict[str, Any]) -> dict[str, Any]:
    sector_raw = str(payload.get("sector", "big tech")).lower()
    symbols = payload.get("symbols")
    if not symbols:
        symbols = SECTOR_COMPETITORS.get(sector_raw, SECTOR_COMPETITORS["big tech"])
    symbols = [str(s).upper() for s in symbols][:7]

    # Semaphore limits concurrent Finviz scraping to 3 at a time (P-3)
    _sem = asyncio.Semaphore(3)

    async def _load_with_sem(sym: str):
        async with _sem:
            return await _load_stock_context(sym)

    contexts = await asyncio.gather(*[_load_with_sem(s) for s in symbols])
    comps = []
    for ctx in contexts:
        ov = ctx["overview"]
        q = ctx["quote"]
        history = ctx["history"]
        returns = _daily_returns(history)
        one_year = (sum(returns[-252:]) if len(returns) >= 252 else sum(returns)) if returns else 0
        roe = _safe_pct(ov.get("roe")) or 0
        margin = _safe_pct(ov.get("profit_margin")) or 0
        r_and_d_proxy = _safe_pct(ov.get("sales_past_5y")) or 0
        moat_score = roe * 100 + margin * 80 + r_and_d_proxy * 40
        comps.append(
            {
                "symbol": ctx["symbol"],
                "market_cap": _safe_float(ov.get("market_cap")) or 0,
                "revenue": _safe_float(ov.get("revenue")) or 0,
                "profit_margin": margin,
                "roe": roe,
                "one_year_price_change_proxy": one_year,
                "moat_rating": "strong" if moat_score > 35 else "moderate" if moat_score > 20 else "weak",
                "management_quality": round(min(10, max(1, 2 + roe * 30 + margin * 20))),
                "innovation_proxy": r_and_d_proxy,
                "price": q.get("price"),
            }
        )

    ranked = sorted(comps, key=lambda x: (x["moat_rating"] == "strong", x["management_quality"], x["profit_margin"]), reverse=True)
    winner = ranked[0] if ranked else None
    winner_context = next((ctx for ctx in contexts if ctx.get("symbol") == winner["symbol"]), {}) if winner else {}
    top2 = ranked[:2]
    swot = []
    for comp in top2:
        swot.append(
            {
                "symbol": comp["symbol"],
                "strengths": ["Scale advantages", "Margin profile", "Capital allocation discipline"],
                "weaknesses": ["Valuation sensitivity"],
                "opportunities": ["AI/new product cycle", "International expansion"],
                "threats": ["Regulatory pressure", "Disruption risk"],
            }
        )

    markdown = "\n".join(
        [
            f"# Bain Competitive Landscape: {sector_raw.title()}",
            "",
            _to_markdown_table(
                ["Ticker", "Market Cap", "Revenue", "Profit Margin", "Moat", "Mgmt Quality"],
                [
                    [
                        c["symbol"],
                        _fmt_num(c["market_cap"], 0),
                        _fmt_num(c["revenue"], 0),
                        _fmt_pct(c["profit_margin"]),
                        c["moat_rating"],
                        c["management_quality"],
                    ]
                    for c in ranked
                ],
            ),
            "",
            f"Best pick: **{winner['symbol']}**" if winner else "No winner.",
            "",
            "## Winner Catalysts (Web)",
            _to_markdown_table(
                ["Headline", "Source"],
                [[h.get("title", "N/A"), h.get("source", "N/A")] for h in (winner_context.get("headlines", [])[:4] or [])]
                or [["N/A", "N/A"]],
            ),
        ]
    )
    return {
        "report_type": "bain_competitive",
        "title": "Bain Competitive Analysis",
        "generated_at": _now_iso(),
        "data": {
            "sector": sector_raw,
            "companies": ranked,
            "best_pick": winner,
            "swot_top2": swot,
            "sector_threats": ["Regulatory risk", "Rate sensitivity", "Supply-chain volatility"],
            "subagent_trace": (winner_context or {}).get("subagent_trace", []),
        },
        "markdown": markdown,
        "assumptions": ["Market share trend is proxied by relative price-performance and scale metrics."],
        "limitations": ["Direct market-share datasets are not integrated in this version."],
        "sources_used": ["market_data_provider", "finviz", "tavily_financial_news"],
    }


async def build_renaissance_pattern(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = _extract_ticker(payload)
    if not ticker:
        raise ValueError("Ticker is required for pattern analysis.")
    period_years = int(payload.get("years", 5) or 5)
    days = max(252, min(2520, period_years * 252))

    # Parallelize the long history fetch with the general stock context and market movers
    tasks = {
        "history_long": get_unified_history(ticker, days=days),
        "movers": get_unified_market_movers(),
        "ctx": _load_stock_context(ticker),
    }
    
    # We use a longer timeout for the history gather, but we want to survive partial failures.
    keys = list(tasks.keys())
    results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results = dict(zip(keys, results_list))

    def _get_val(k, default):
        v = results.get(k)
        if v is None or isinstance(v, Exception):
            return default
        return v

    history = _get_val("history_long", [])
    ctx = _get_val("ctx", {})
    movers = _get_val("movers", {})

    # Fallback to context history (365 days) if long history failed
    if not history and ctx:
        history = ctx.get("history", [])

    if not history:
        # One last attempt for history if it's the only thing missing
        history = await get_unified_history(ticker, days=365)

    if not history:
        raise ValueError(f"No history found for {ticker}. Analysis requires at least 1 year of price data.")

    returns = _daily_returns(history)
    monthly_map: dict[int, list[float]] = {i: [] for i in range(1, 13)}
    dow_map: dict[int, list[float]] = {i: [] for i in range(0, 5)}
    for i in range(1, len(history)):
        try:
            dt_str = str(history[i]["date"])
            if not dt_str:
                continue
            dt = datetime.fromisoformat(dt_str)
            r = returns[i - 1] if i - 1 < len(returns) else 0
            monthly_map[dt.month].append(r)
            if dt.weekday() < 5:
                dow_map[dt.weekday()].append(r)
        except Exception:
            continue

    monthly_avg = {m: (statistics.mean(v) if v else 0) for m, v in monthly_map.items()}
    dow_avg = {d: (statistics.mean(v) if v else 0) for d, v in dow_map.items()}
    best_month = max(monthly_avg, key=lambda m: monthly_avg[m]) if monthly_avg else 1
    worst_month = min(monthly_avg, key=lambda m: monthly_avg[m]) if monthly_avg else 1
    best_day = max(dow_avg, key=lambda d: dow_avg[d]) if dow_avg else 0
    worst_day = min(dow_avg, key=lambda d: dow_avg[d]) if dow_avg else 0

    # Extract data from context instead of re-fetching
    insiders = ctx.get("insiders") or {}
    overview = ctx.get("overview") or {}
    short_float = _safe_pct(overview.get("short_float"))

    markdown = "\n".join(
        [
            f"# Renaissance Pattern Memo: {ticker}",
            "",
            _to_markdown_table(
                ["Pattern", "Finding"],
                [
                    ["Best month", str(best_month)],
                    ["Worst month", str(worst_month)],
                    ["Best weekday (0=Mon)", str(best_day)],
                    ["Worst weekday (0=Mon)", str(worst_day)],
                    ["Short float", _fmt_pct(short_float)],
                    ["Recent insider records", len(insiders.get("insider_trades", []))],
                ],
            ),
            "",
            "## Recent Event Signals",
            _to_markdown_table(
                ["Headline", "Source"],
                [[h.get("title", "N/A"), h.get("source", "N/A")] for h in (ctx.get("headlines", [])[:4] or [])]
                or [["N/A", "N/A"]],
            ),
        ]
    )
    return {
        "report_type": "renaissance_pattern",
        "title": "Renaissance Pattern Finder",
        "generated_at": _now_iso(),
        "data": {
            "ticker": ticker,
            "best_month": best_month,
            "worst_month": worst_month,
            "best_weekday": best_day,
            "worst_weekday": worst_day,
            "monthly_averages": monthly_avg,
            "weekday_averages": dow_avg,
            "insider_activity": insiders,
            "short_interest_proxy": short_float,
            "sector_rotation_signal": movers,
            "edge_summary": f"Seasonality favors month {best_month} and weekday {best_day}.",
            "subagent_trace": ctx.get("subagent_trace", []),
        },
        "markdown": markdown,
        "assumptions": ["Patterns are based on historical daily return seasonality."],
        "limitations": ["Event correlations (Fed/CPI/options flow) use proxy signals without dedicated event database."],
        "sources_used": ["market_data_provider", "finviz", "tavily_financial_news", "tavily_news_sentiment"],
    }


async def build_mckinsey_macro(payload: dict[str, Any]) -> dict[str, Any]:
    holdings = await _resolve_portfolio_input(payload)
    macro = await get_key_indicators()

    fed = (macro.get("fed_funds") or {}).get("value")
    cpi = (macro.get("cpi") or {}).get("value")
    unemp = (macro.get("unemployment") or {}).get("value")
    ten_y = (macro.get("10y_treasury") or {}).get("value")

    cycle = "late-cycle"
    if fed and fed < 2:
        cycle = "early-cycle"
    elif fed and fed > 4.5:
        cycle = "slowdown / restrictive"

    adjustments = [
        "Trim high-duration growth exposure by 5-10% if rates stay restrictive.",
        "Add quality value + healthcare defensives for inflation-resilient cash flows.",
        "Hold a short-duration bond sleeve for optionality around policy pivots.",
    ]
    if holdings:
        top = sorted(holdings, key=lambda x: x["weight"], reverse=True)[:3]
        top_txt = ", ".join([f"{t['symbol']} ({t['weight']*100:.1f}%)" for t in top])
        adjustments.append(f"Top holdings concentration: {top_txt}.")

    markdown = "\n".join(
        [
            "# McKinsey Macro Strategy Briefing",
            "",
            _to_markdown_table(
                ["Indicator", "Latest"],
                [
                    ["Fed Funds", str(fed)],
                    ["CPI", str(cpi)],
                    ["Unemployment", str(unemp)],
                    ["10Y Treasury", str(ten_y)],
                    ["Cycle Assessment", cycle],
                ],
            ),
            "",
            "## Action Plan",
            "\n".join([f"- {a}" for a in adjustments]),
        ]
    )
    return {
        "report_type": "mckinsey_macro",
        "title": "McKinsey Macro Economic Impact Report",
        "generated_at": _now_iso(),
        "data": {
            "macro_snapshot": macro,
            "cycle_assessment": cycle,
            "recommended_adjustments": adjustments,
            "timeline": "Most macro transmission effects expected over the next 3-12 months.",
        },
        "markdown": markdown,
        "assumptions": ["Macro effects are interpreted through standard growth/value and duration sensitivity frameworks."],
        "limitations": ["This briefing does not include real-time central bank event transcript parsing."],
        "sources_used": ["fred", "market_data_provider", "portfolio_db"],
    }


def _build_tool_plan(report_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    ticker = _extract_ticker(payload)
    plan: list[dict[str, Any]] = []

    if ticker:
        plan.append({"tool": "market_data_provider.get_unified_quote", "reason": f"Live price anchor for {ticker}"})
        plan.append({"tool": "market_data_provider.get_unified_history", "reason": f"Trend/volatility history for {ticker}"})
        plan.append({"tool": "finviz.get_company_overview", "reason": f"Fundamentals for {ticker}"})
        plan.append({"tool": "finviz.get_analyst_ratings", "reason": f"Street signals for {ticker}"})
        plan.append({"tool": "tavily.get_news_sentiment", "reason": f"Recent narrative/sentiment for {ticker}"})
    if report_type in {"morgan_dcf", "mckinsey_macro"}:
        plan.append({"tool": "fred.get_key_indicators", "reason": "Macro inputs for discount-rate/cycle assumptions"})
    if report_type in {"bridgewater_risk", "blackrock_builder", "mckinsey_macro"}:
        plan.append({"tool": "portfolio_repo.get_holdings", "reason": "Portfolio-aware recommendations"})
    return plan


def _default_sources(report_type: str) -> list[str]:
    mapping = {
        "goldman_screener": ["market_data_provider", "finviz", "tavily_news_sentiment"],
        "morgan_dcf": ["market_data_provider", "finviz", "fred", "tavily_financial_news"],
        "bridgewater_risk": ["portfolio_db", "market_data_provider", "finviz"],
        "jpm_earnings": ["market_data_provider", "finviz", "tavily_news_sentiment", "tavily_financial_news"],
        "blackrock_builder": ["historical_allocation_proxies"],
        "citadel_technical": ["market_data_provider", "technical_analysis"],
        "harvard_dividend": ["finviz", "market_data_provider"],
        "bain_competitive": ["market_data_provider", "finviz", "tavily_financial_news"],
        "renaissance_pattern": ["market_data_provider", "finviz", "tavily_financial_news"],
        "mckinsey_macro": ["fred", "market_data_provider", "portfolio_db"],
    }
    return mapping.get(report_type, ["market_data_provider", "finviz"])


REPORT_BUILDERS = {
    "goldman_screener": build_goldman_screener,
    "morgan_dcf": build_morgan_dcf,
    "bridgewater_risk": build_bridgewater_risk,
    "jpm_earnings": build_jpm_earnings,
    "blackrock_builder": build_blackrock_builder,
    "citadel_technical": build_citadel_technical,
    "harvard_dividend": build_harvard_dividend,
    "bain_competitive": build_bain_competitive,
    "renaissance_pattern": build_renaissance_pattern,
    "mckinsey_macro": build_mckinsey_macro,
}


async def generate_report(
    report_type: str,
    payload: dict[str, Any],
    *,
    effective_prompt: str | None = None,
) -> dict[str, Any]:
    rt = report_type.strip().lower()
    builder = REPORT_BUILDERS.get(rt)
    if not builder:
        raise ValueError(
            f"Unknown report type '{report_type}'. "
            f"Supported: {', '.join(sorted(REPORT_BUILDERS.keys()))}"
        )
    clean_payload = payload or {}
    result = await builder(clean_payload)
    result["tool_plan"] = _build_tool_plan(rt, clean_payload)
    result.setdefault("sources_used", _default_sources(rt))
    result["prompt_template"] = PROMPT_TEMPLATES[rt]["prompt"]
    result["effective_prompt"] = effective_prompt or PROMPT_TEMPLATES[rt]["prompt"]
    persisted = await save_report_run(rt, clean_payload, result)
    if persisted:
        result["persisted_run_id"] = str(persisted["id"])
    return result


def list_report_types() -> list[dict[str, Any]]:
    return [
        {"id": report_id, "title": meta["title"], "prompt_template": meta["prompt"]}
        for report_id, meta in PROMPT_TEMPLATES.items()
    ]
