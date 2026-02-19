from typing import Any
import asyncio
import statistics
from apps.api.services.builders.helpers import *
from apps.api.agents.technical_analysis.tools import analyze_technicals

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



