from typing import Any
import asyncio
import statistics
from apps.api.services.builders.helpers import *
from apps.api.agents.technical_analysis.tools import analyze_technicals

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



