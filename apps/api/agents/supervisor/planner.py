"""Planner node — analyzes the user query and creates an execution plan."""

import json
import re

import anthropic

from apps.api.config import settings
from apps.api.agents.supervisor.state import SupervisorState, ExecutionPlan, AgentTask
from apps.api.agents.memory.manager import MemoryManager
from apps.api.agents.supervisor.task_runtime import canonical_agent

# Module-level singletons — created once, reused for the lifetime of the process.
_client: anthropic.AsyncAnthropic | None = None
_memory_manager: MemoryManager | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


PLANNER_PROMPT = """You are a financial AI planner. Analyze the user's query and create an execution plan.

Available specialist agents:
- market_data: Real-time quotes, price history, market movers.
- fundamentals: Company overview, analyst ratings, insider trades, SEC filings.
- technicals: RSI, MACD, moving averages, support/resistance.
- sentiment: Reddit sentiment, news sentiment, congressional trades.
- macro: Economic indicators (FRED), Treasury yields, Federal funds rate, sector rotation.
- advisor: Comprehensive investment advice combining multiple data sources.

Rules:
1. Identify the DATA CATEGORIES needed:
   - Specific Stocks/Prices -> market_data
   - Financials/Ratings/Insiders -> fundamentals
   - Technical Indicators (RSI, etc) -> technical_analysis (Note: depends on market_data for history)
   - Social Sentiment/News -> sentiment
   - Macro/Yields/Rates/FRED -> macro
   - Cross-domain summary/Advice -> advisor
2. For simple single-category queries, use ONE agent.
3. MANDATORY SPLITTING: If a query contains multiple data categories (e.g. stock price AND macrometrics), you MUST create SEPARATE steps for each category. DO NOT try to handle everything with one agent.
4. CRITICAL: If a user asks for technical analysis (RSI, moving averages, etc.), you MUST first fetch price history using `market_data`.
   Example:
   Step 1: Agent=market_data, Query="Get price history for AAPL"
   Step 2: Agent=technical_analysis, Query="Calculate RSI for AAPL", Depends_On=["market_data"]
5. For mixed stock and macro queries (e.g., "how is inflation affecting NVDA?"), use a plan with both macro and advisor agents.
   Example query: "What is the 10Y yield and AAPL price?"
   Step 1: Agent=macro, Query="Get 10Y Treasury yield"
   Step 2: Agent=market_data, Query="Get AAPL price"

Respond with valid JSON matching this schema:
{
    "reasoning": "Brief explanation of your plan",
    "steps": [
        {
            "agent": "agent_name",
            "query": "specific sub-query",
            "depends_on": []
        }
    ],
    "parallel_groups": [["agent1", "agent2"]]
}
"""


def _extract_json_candidate(text: str) -> str:
    cleaned = (text or "").strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        return match.group(0)
    return cleaned


async def planner_node(state: SupervisorState) -> dict:
    """Analyze the user query and determine which agents to call."""
    messages = state.get("messages", [])
    if not messages:
        return {"final_response": "I didn't receive a message. How can I help?"}

    # Extract user message
    user_message = _latest_user_message(messages)
    if not user_message:
        user_message = str(messages[-1].content) if hasattr(messages[-1], "content") else str(messages[-1])

    # Resolve short/ambiguous follow-ups ("yeah", "go on", "that") against prior turn context.
    effective_user_message = _resolve_follow_up_context(messages, user_message)


    # Include memory context if available
    memory_manager = _get_memory_manager()
    # Simple semantic search using resolved user intent
    memory_results = await memory_manager.get_relevant_context(
        effective_user_message,
        k=4,
        user_id=state.get("user_id"),
        tenant_id=state.get("tenant_id"),
        conversation_id=state.get("conversation_id"),
    )
    
    memory_text = ""
    if memory_results:
        memory_text = "\n\nRelevant past context:\n"
        for mem in memory_results[:2]:
            memory_text += f"- {mem.get('content', '')[:220]}\n"

    client = _get_client()
    try:
        response = await client.messages.create(
            model=settings.ROUTING_MODEL,
            max_tokens=1000,
            system=PLANNER_PROMPT,
            messages=[
                {"role": "user", "content": f"{effective_user_message}{memory_text}"}
            ],
        )

        raw_text = response.content[0].text.strip() if response.content else ""
        plan_text = _extract_json_candidate(raw_text)
        plan_dict = json.loads(plan_text)
        
        # Validate with Pydantic, then normalize task ids/dependencies for runtime routing.
        raw_plan = ExecutionPlan(**plan_dict)
        plan = _normalize_execution_plan(raw_plan, user_message=effective_user_message)
        pending_agents = [step.agent for step in plan.steps]
        task_status = {step.task_id: "pending" for step in plan.steps}

        return {
            "plan": plan,
            "pending_agents": pending_agents,
            "task_status": task_status,
            "current_step": 0,
            "memory_context": memory_results # Store in state for other agents
        }

    except Exception as e:
        print(f"Planner error: {e}")
        # Fallback: deterministic baseline route with optional synthesis.
        fallback_steps: list[AgentTask] = [
            AgentTask(task_id="t1_market_data", agent="market_data", query=effective_user_message)
        ]

        if _needs_fundamentals(effective_user_message):
            fallback_steps.append(
                AgentTask(task_id="t2_fundamentals", agent="fundamentals", query=effective_user_message)
            )

        if _requires_advisor(effective_user_message):
            fallback_steps.append(
                AgentTask(
                    task_id=f"t{len(fallback_steps) + 1}_advisor",
                    agent="advisor",
                    query=effective_user_message,
                    depends_on=[step.task_id for step in fallback_steps],
                )
            )

        fallback_plan = ExecutionPlan(
            reasoning="Fallback due to planning error",
            steps=fallback_steps,
            parallel_groups=[]
        )
        return {
            "plan": fallback_plan,
            "pending_agents": [step.agent for step in fallback_steps],
            "task_status": {step.task_id: "pending" for step in fallback_steps},
            "current_step": 0,
            "memory_context": []
        }


def _normalize_execution_plan(plan: ExecutionPlan, user_message: str = "") -> ExecutionPlan:
    normalized_steps: list[AgentTask] = []
    seen_task_ids: set[str] = set()
    latest_task_by_agent: dict[str, str] = {}

    for idx, step in enumerate(plan.steps):
        agent = canonical_agent(step.agent)
        raw_task_id = str(getattr(step, "task_id", "") or "").strip()
        task_id = raw_task_id or f"t{idx + 1}_{agent}"
        if task_id in seen_task_ids:
            task_id = f"{task_id}_{idx + 1}"

        deps: list[str] = []
        for dep in step.depends_on or []:
            dep_token = str(dep or "").strip()
            if not dep_token:
                continue
            if dep_token in seen_task_ids:
                deps.append(dep_token)
                continue
            dep_agent = canonical_agent(dep_token)
            dep_task_id = latest_task_by_agent.get(dep_agent)
            if dep_task_id:
                deps.append(dep_task_id)

        deduped_deps: list[str] = []
        for dep in deps:
            if dep not in deduped_deps and dep != task_id:
                deduped_deps.append(dep)

        normalized_step = AgentTask(
            task_id=task_id,
            agent=agent,
            query=str(step.query or ""),
            depends_on=deduped_deps,
        )
        normalized_steps.append(normalized_step)
        seen_task_ids.add(task_id)
        latest_task_by_agent[agent] = task_id

    normalized_parallel_groups = [
        [canonical_agent(agent) for agent in group if canonical_agent(agent)]
        for group in (plan.parallel_groups or [])
    ]

    # Default dependency upgrades for better output quality.
    for idx, step in enumerate(normalized_steps):
        if step.agent == "advisor" and not step.depends_on:
            prior_ids = [s.task_id for s in normalized_steps[:idx]]
            if prior_ids:
                step.depends_on = prior_ids
        if step.agent == "technical_analysis" and not step.depends_on:
            prior_market = [s.task_id for s in normalized_steps[:idx] if s.agent == "market_data"]
            if prior_market:
                step.depends_on = prior_market

    # Keep a single advisor step to avoid repeated synthesis loops from noisy plan JSON.
    advisor_indices = [idx for idx, step in enumerate(normalized_steps) if step.agent == "advisor"]
    if len(advisor_indices) > 1:
        keep_idx = advisor_indices[-1]
        deduped_steps: list[AgentTask] = []
        for idx, step in enumerate(normalized_steps):
            if step.agent == "advisor" and idx != keep_idx:
                continue
            deduped_steps.append(step)
        normalized_steps = deduped_steps
        for idx, step in enumerate(normalized_steps):
            if step.agent == "advisor":
                step.depends_on = [s.task_id for s in normalized_steps[:idx]]
                break

    # Force a synthesis/advisory pass for explanatory intent (e.g., "why did X move").
    if _requires_advisor(user_message):
        has_advisor = any(step.agent == "advisor" for step in normalized_steps)
        if not has_advisor:
            advisor_task_id = f"t{len(normalized_steps) + 1}_advisor"
            advisor_step = AgentTask(
                task_id=advisor_task_id,
                agent="advisor",
                query=user_message or "Synthesize prior findings into a direct answer.",
                depends_on=[s.task_id for s in normalized_steps],
            )
            normalized_steps.append(advisor_step)

    return ExecutionPlan(
        reasoning=plan.reasoning,
        steps=normalized_steps,
        parallel_groups=normalized_parallel_groups,
    )


def _requires_advisor(user_message: str) -> bool:
    text = (user_message or "").strip().lower()
    if not text:
        return False
    triggers = (
        "why ",
        "why did",
        "what caused",
        "what drove",
        "explain",
        "compare",
        " vs ",
        "versus",
        "brief",
        "memo",
        "valuation",
        "dcf",
        "portfolio",
        "dividend",
        "risk",
        "report card",
        "catalyst",
        "trade plan",
        "entry zone",
        "invalidation",
        "should i",
        "recommend",
        "buy or sell",
    )
    return any(token in text for token in triggers)


def _needs_fundamentals(user_message: str) -> bool:
    text = (user_message or "").strip().lower()
    if not text:
        return False
    triggers = (
        "fundamental",
        "valuation",
        "dcf",
        "earnings",
        "dividend",
        "compare",
        "versus",
        " vs ",
        "sector",
        "portfolio",
        "risk",
    )
    return any(token in text for token in triggers)


def _latest_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            return str(getattr(msg, "content", "") or "")
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", "") or "")
    return ""


def _previous_user_message(messages: list, latest: str) -> str:
    seen_latest = False
    for msg in reversed(messages):
        content = ""
        role = ""
        if hasattr(msg, "type"):
            role = "user" if msg.type == "human" else str(getattr(msg, "type", ""))
            content = str(getattr(msg, "content", "") or "")
        elif isinstance(msg, dict):
            role = str(msg.get("role", ""))
            content = str(msg.get("content", "") or "")
        if role != "user":
            continue
        if not seen_latest and content.strip() == (latest or "").strip():
            seen_latest = True
            continue
        if seen_latest and content.strip():
            return content.strip()
    return ""


def _latest_assistant_message(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai":
            return str(getattr(msg, "content", "") or "")
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return str(msg.get("content", "") or "")
    return ""


def _is_affirmative_follow_up(text: str) -> bool:
    value = (text or "").strip().lower()
    if not value:
        return False
    confirmations = {
        "yes",
        "yeah",
        "yep",
        "sure",
        "ok",
        "okay",
        "go ahead",
        "do it",
        "please do",
        "sounds good",
    }
    return value in confirmations


def _is_ambiguous_follow_up(text: str) -> bool:
    value = (text or "").strip().lower()
    if not value:
        return False
    if len(value.split()) <= 4:
        return True
    vague_tokens = ("that", "this", "same", "continue", "go on", "more on that")
    return any(token in value for token in vague_tokens)


def _extract_primary_symbol(text: str) -> str:
    if not text:
        return ""
    dollar = re.findall(r"\$([A-Z]{1,5})\b", text)
    if dollar:
        return dollar[0].upper()
    upper = re.findall(r"\b([A-Z]{2,5})\b", text)
    stop_words = {"RSI", "MACD", "SMA", "EMA", "USD", "THE", "AND"}
    for token in upper:
        t = token.upper()
        if t not in stop_words:
            return t
    alias_map = {
        "rivian": "RIVN",
        "apple": "AAPL",
        "microsoft": "MSFT",
        "tesla": "TSLA",
        "nvidia": "NVDA",
        "amazon": "AMZN",
        "meta": "META",
        "google": "GOOGL",
        "alphabet": "GOOGL",
    }
    lowered = text.lower()
    for name, ticker in alias_map.items():
        if name in lowered:
            return ticker
    return ""


def _resolve_follow_up_context(messages: list, user_message: str) -> str:
    current = (user_message or "").strip()
    if not current:
        return user_message

    previous_user = _previous_user_message(messages, latest=current)
    if not previous_user:
        return current

    previous_assistant = _latest_assistant_message(messages).lower()
    primary_symbol = _extract_primary_symbol(previous_user)

    if _is_affirmative_follow_up(current):
        if "catalyst probability breakdown" in previous_assistant and "trade plan" in previous_assistant:
            symbol_hint = f" for {primary_symbol}" if primary_symbol else ""
            return (
                f"Provide a catalyst probability breakdown{symbol_hint}, plus a trade plan "
                "(entry zone, invalidation, stop, and target). Continue the prior request context: "
                f"{previous_user}"
            )
        return (
            f"User confirmed to continue. Refine and continue prior request: {previous_user}. "
            f"Keep same symbol/topic{f' ({primary_symbol})' if primary_symbol else ''} unless user explicitly changes it."
        )

    if _is_ambiguous_follow_up(current):
        return (
            f"Follow-up in same thread: {current}. Continue and refine prior request: {previous_user}. "
            f"Keep same symbol/topic{f' ({primary_symbol})' if primary_symbol else ''} unless user explicitly changes it."
        )

    return current
