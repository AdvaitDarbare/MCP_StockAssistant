"""Report engine for advanced stock/portfolio workflows."""

from __future__ import annotations
from typing import Any

from apps.api.db.report_repo import save_report_run
from apps.api.services.report_prompts import PROMPT_TEMPLATES
from apps.api.services.builders.helpers import _now_iso, _extract_ticker

# Import extracted builders
from apps.api.services.builders.valuation import build_morgan_dcf, build_jpm_earnings
from apps.api.services.builders.screening import build_goldman_screener, build_harvard_dividend, build_bain_competitive
from apps.api.services.builders.portfolio import build_bridgewater_risk, build_blackrock_builder, build_mckinsey_macro
from apps.api.services.builders.technical import build_citadel_technical, build_renaissance_pattern

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
