from typing import Any
import asyncio
import statistics
from apps.api.services.builders.helpers import *
from apps.api.agents.technical_analysis.tools import analyze_technicals

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



