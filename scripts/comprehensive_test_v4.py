"""
Comprehensive test suite for AI Stock Assistant.
Tests: all 10 institutional reports, multi-turn chat, multi-question,
       multi-tool, complex reasoning, and edge cases.
"""
import asyncio
import json
import time
import httpx
import requests

BASE_CHAT_URL = "http://127.0.0.1:8001/api/chat"
BASE_REPORTS_URL = "http://127.0.0.1:8001/api/reports"
OWNER_KEY = "comprehensive-test"

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results = {"reports": {}, "chat": {}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def run_chat_query(
    label: str,
    query: str,
    conversation_id: str | None = None,
    user_id: str = "tester",
    expect_agents: set[str] | None = None,
    expect_tools: set[str] | None = None,
) -> tuple[str, dict]:
    """Stream a chat query and return (conversation_id, result_dict)."""
    if conversation_id is None:
        conversation_id = f"test-{int(time.time())}"

    print(f"\n--- CHAT: {label} ---")
    print(f"    Query: {query[:80]}{'...' if len(query) > 80 else ''}")

    payload = {
        "messages": [{"role": "user", "content": query}],
        "conversation_id": conversation_id,
        "user_id": user_id,
    }

    agents: set[str] = set()
    tools: set[str] = set()
    final_text = ""
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream("POST", BASE_CHAT_URL, json=payload) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                    t = data.get("type")
                    if t == "agent_start":
                        agents.add(data.get("agent", ""))
                    elif t == "tool_start":
                        tools.add(data.get("tool", ""))
                    elif t == "final":
                        final_text = data.get("content", "")
                    elif t == "error":
                        errors.append(data.get("message", ""))
                except json.JSONDecodeError:
                    continue

    ok = bool(final_text) and not errors
    status = PASS if ok else FAIL

    # Check expectations
    if expect_agents and not expect_agents.issubset(agents):
        missing = expect_agents - agents
        print(f"    {WARN} Expected agents {missing} not invoked")
    if expect_tools and not expect_tools.issubset(tools):
        missing = expect_tools - tools
        print(f"    {WARN} Expected tools {missing} not called")

    print(f"    {status} Agents: {agents}")
    print(f"    {status} Tools:  {tools}")
    print(f"    Response: {len(final_text)} chars | Errors: {errors or 'none'}")
    if final_text:
        print(f"    Preview: {final_text[:120]}...")

    results["chat"][label] = {
        "ok": ok,
        "agents": list(agents),
        "tools": list(tools),
        "response_len": len(final_text),
        "errors": errors,
    }
    return conversation_id, results["chat"][label]


def run_report(report_id: str, payload: dict, label: str) -> bool:
    """POST to the reports endpoint and return success bool."""
    print(f"\n--- REPORT: {label} ({report_id}) ---")
    try:
        resp = requests.post(
            f"{BASE_REPORTS_URL}/{report_id}",
            json={"payload": payload, "owner_key": OWNER_KEY},
            timeout=120,
        )
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", report_id)
            md_len = len(data.get("markdown", ""))
            print(f"    {PASS} {title} | markdown: {md_len} chars")
            results["reports"][report_id] = {"ok": True, "title": title}
            return True
        else:
            print(f"    {FAIL} HTTP {resp.status_code}: {resp.text[:200]}")
            results["reports"][report_id] = {"ok": False, "error": resp.text[:200]}
            return False
    except Exception as e:
        print(f"    {FAIL} Exception: {e}")
        results["reports"][report_id] = {"ok": False, "error": str(e)}
        return False


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("  AI STOCK ASSISTANT — COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    # -----------------------------------------------------------------------
    # 1. ALL 10 INSTITUTIONAL REPORTS
    # -----------------------------------------------------------------------
    print("\n\n### SECTION 1: Institutional Reports (all 10) ###")

    report_tests = [
        ("goldman_screener",   {"limit": 3},                                    "Goldman Sachs Screener"),
        ("morgan_dcf",         {"ticker": "AAPL"},                              "Morgan Stanley DCF — AAPL"),
        ("bridgewater_risk",   {"holdings": [{"symbol": "NVDA", "weight": 1.0}]}, "Bridgewater Risk — NVDA"),
        ("jpm_earnings",       {"ticker": "TSLA"},                              "JPMorgan Earnings — TSLA"),
        ("citadel_technical",  {"ticker": "MSFT"},                              "Citadel Technical — MSFT"),
        ("harvard_dividend",   {"tickers": ["JNJ", "KO", "PG"]},               "Harvard Dividend Strategy"),
        ("bain_competitive",   {"sector": "technology"},                        "Bain Competitive Analysis"),
        ("renaissance_pattern",{"tickers": ["AAPL", "MSFT", "NVDA"]},          "Renaissance Pattern Finder"),
        ("blackrock_builder",  {"risk_profile": "moderate"},                    "BlackRock Portfolio Builder"),
        ("mckinsey_macro",     {"sectors": ["technology", "energy"]},           "McKinsey Macro Impact"),
    ]

    report_pass = sum(run_report(rid, pay, lbl) for rid, pay, lbl in report_tests)
    print(f"\n  Reports: {report_pass}/{len(report_tests)} passed")

    # -----------------------------------------------------------------------
    # 2. SINGLE-TOOL CHAT QUERIES
    # -----------------------------------------------------------------------
    print("\n\n### SECTION 2: Single-Tool Chat Queries ###")

    await run_chat_query(
        "Stock Quote (get_quote)",
        "What is AAPL's current stock price?",
    )
    await run_chat_query(
        "Price History (get_historical_prices)",
        "Show me TSLA's price history for the last 10 days.",
    )
    await run_chat_query(
        "Company Profile (get_company_profile)",
        "Give me a company profile for NVDA.",
    )
    await run_chat_query(
        "Market Movers (get_market_movers)",
        "What are today's top market movers?",
    )
    await run_chat_query(
        "Stock News (get_stock_news)",
        "What's the latest news on AMZN?",
    )
    await run_chat_query(
        "Macro Indicators (get_macro_summary)",
        "What are the current key macroeconomic indicators?",
        expect_agents={"macro"},
    )

    # -----------------------------------------------------------------------
    # 3. MULTI-TOOL SINGLE-TURN QUERIES
    # -----------------------------------------------------------------------
    print("\n\n### SECTION 3: Multi-Tool / Multi-Agent Single-Turn ###")

    await run_chat_query(
        "Multi-Question: Macro + Stock Price",
        "What is the current US unemployment rate AND what is NVDA's current price?",
        expect_agents={"macro", "market_data"},
    )
    await run_chat_query(
        "Multi-Question: Fundamentals + Quote",
        "Give me AAPL's P/E ratio and its current stock price.",
        expect_agents={"fundamentals", "market_data"},
    )
    await run_chat_query(
        "Technical + Market Data",
        "Get MSFT's price history and compute its RSI.",
        expect_agents={"market_data", "technical_analysis"},
    )
    await run_chat_query(
        "Multi-Symbol History Compare",
        "Compare the last 5 trading days of AAPL vs MSFT vs NVDA.",
    )

    # -----------------------------------------------------------------------
    # 4. MULTI-TURN CONVERSATION
    # -----------------------------------------------------------------------
    print("\n\n### SECTION 4: Multi-Turn Conversation ###")

    conv_id, _ = await run_chat_query(
        "Turn 1 — Initial stock query",
        "Tell me about AAPL's current stock price and recent news.",
    )
    await asyncio.sleep(1)

    conv_id, _ = await run_chat_query(
        "Turn 2 — Follow-up comparison",
        "Compare that to MSFT's current valuation.",
        conversation_id=conv_id,
    )
    await asyncio.sleep(1)

    await run_chat_query(
        "Turn 3 — Affirmative follow-up",
        "yes",
        conversation_id=conv_id,
    )

    # -----------------------------------------------------------------------
    # 5. COMPLEX / REASONING QUERIES
    # -----------------------------------------------------------------------
    print("\n\n### SECTION 5: Complex Reasoning Queries ###")

    await run_chat_query(
        "Cross-Domain: Macro Impact on Stock",
        "How does the current inflation environment and Fed rate policy affect NVDA's valuation?",
        expect_agents={"macro", "advisor"},
    )
    await run_chat_query(
        "Buy/Sell Recommendation",
        "Should I buy or sell AMD right now? Give me a full analysis.",
        expect_agents={"advisor"},
    )
    await run_chat_query(
        "Portfolio Risk Assessment",
        "I hold AAPL, MSFT, and NVDA equally. What's my portfolio risk?",
        expect_agents={"advisor"},
    )
    await run_chat_query(
        "Sector Rotation Analysis",
        "Which sectors are benefiting most from the current macro environment?",
        expect_agents={"macro"},
    )

    # -----------------------------------------------------------------------
    # 6. EDGE CASES
    # -----------------------------------------------------------------------
    print("\n\n### SECTION 6: Edge Cases ###")

    await run_chat_query(
        "Non-Existent Ticker",
        "What is the stock price of ZZZZZ?",
    )
    await run_chat_query(
        "Ambiguous Query",
        "What do you think about the market?",
    )
    await run_chat_query(
        "Very Short Query",
        "AAPL?",
    )

    # -----------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------
    print("\n\n" + "=" * 60)
    print("  FINAL SUMMARY")
    print("=" * 60)

    total_reports = len(results["reports"])
    passed_reports = sum(1 for v in results["reports"].values() if v["ok"])
    total_chat = len(results["chat"])
    passed_chat = sum(1 for v in results["chat"].values() if v["ok"])

    print(f"\n  Reports:  {passed_reports}/{total_reports} passed")
    print(f"  Chat:     {passed_chat}/{total_chat} passed")

    failed_reports = [k for k, v in results["reports"].items() if not v["ok"]]
    failed_chat = [k for k, v in results["chat"].items() if not v["ok"]]

    if failed_reports:
        print(f"\n  {FAIL} Failed Reports: {failed_reports}")
    if failed_chat:
        print(f"\n  {FAIL} Failed Chat:    {failed_chat}")

    if not failed_reports and not failed_chat:
        print(f"\n  {PASS} ALL TESTS PASSED")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
