from typing import Any
import asyncio
import statistics
from apps.api.services.builders.helpers import *
from apps.api.agents.technical_analysis.tools import analyze_technicals

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



