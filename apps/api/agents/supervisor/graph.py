"""LangGraph supervisor workflow.

Architecture: Two-tier agent hierarchy
  Tier 1 — Research (parallel, tool-only):  market_data, fundamentals, sentiment, macro
  Tier 2 — Synthesis (sequential, LLM):     technical_analysis (needs market_data), advisor

A `research_gate` node sits between the two tiers and enforces that all Tier-1
agents have completed before Tier-2 agents are allowed to run.  This removes the
dependency on the planner prompt alone to enforce ordering.

Safety:
  - `recursion_limit=25` prevents infinite routing loops (G-2).
  - `MemoryManager` is a module-level singleton (A-2 / G-4).
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from apps.api.agents.supervisor.state import SupervisorState
from apps.api.agents.content_utils import normalize_content_to_text
from apps.api.agents.supervisor.planner import planner_node
from apps.api.agents.supervisor.task_runtime import canonical_agent, deps_satisfied
from apps.api.agents.market_data.agent import market_data_node
from apps.api.agents.technical_analysis.agent import technical_analysis_node
from apps.api.agents.fundamentals.agent import fundamentals_node
from apps.api.agents.sentiment.agent import sentiment_node

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported agents
# ---------------------------------------------------------------------------

RESEARCH_AGENTS = {"market_data", "fundamentals", "sentiment", "macro"}
SYNTHESIS_AGENTS = {"technical_analysis", "advisor"}
SUPPORTED_AGENTS = RESEARCH_AGENTS | SYNTHESIS_AGENTS

# ---------------------------------------------------------------------------
# Module-level MemoryManager singleton (A-2 / G-4)
# ---------------------------------------------------------------------------

from apps.api.agents.memory.manager import MemoryManager

_memory_manager: MemoryManager | None = None


def _get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


# ---------------------------------------------------------------------------
# Router node — marks dependency-blocked tasks as skipped
# ---------------------------------------------------------------------------

async def router_node(state: SupervisorState):
    """Mark dependency-blocked tasks before conditional routing picks the next node."""
    plan = state.get("plan")
    if not plan or not getattr(plan, "steps", None):
        return {}

    task_status = dict(state.get("task_status", {}) or {})
    changed = False
    for step in plan.steps:
        current = task_status.get(step.task_id, "pending")
        if current != "pending":
            continue
        dep_states = [task_status.get(dep, "pending") for dep in (step.depends_on or [])]
        if any(dep_state in {"failed", "skipped"} for dep_state in dep_states):
            task_status[step.task_id] = "skipped"
            changed = True
    if not changed:
        return {}
    return {"task_status": task_status}


# ---------------------------------------------------------------------------
# Research gate — enforces Tier-1 completion before Tier-2 starts (G-3)
# ---------------------------------------------------------------------------

async def research_gate_node(state: SupervisorState):
    """No-op gate node; routing logic in route_after_research enforces the tier boundary."""
    return {}


# ---------------------------------------------------------------------------
# Aggregator node
# ---------------------------------------------------------------------------

async def aggregator_node(state: SupervisorState):
    """Synthesise results from all agents and persist to memory."""
    results = state.get("agent_results", {})

    if not results:
        final_response = "No agents were executed."
    else:
        advisor_result = results.get("advisor")
        if isinstance(advisor_result, dict):
            advisor_text = normalize_content_to_text(advisor_result.get("content", "")).strip()
            final_response = advisor_text if advisor_text else _compose_multi_agent_summary(results)
        else:
            final_response = _compose_multi_agent_summary(results)

    # Persist to memory using the singleton (A-2 / G-4)
    try:
        messages = state.get("messages", [])
        user_message = ""
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                user_message = msg.content
                break
            elif isinstance(msg, dict) and msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if user_message:
            memory_manager = _get_memory_manager()
            await memory_manager.save_interaction(
                user_input=user_message,
                agent_output=final_response,
                metadata={
                    "conversation_id": state.get("conversation_id"),
                    "user_id": state.get("user_id"),
                    "tenant_id": state.get("tenant_id"),
                },
            )
    except Exception as e:
        logger.warning("Memory save error: %s", e)

    return {"final_response": final_response}


def _compose_multi_agent_summary(results: dict) -> str:
    ordered_agents = [
        "market_data",
        "fundamentals",
        "technical_analysis",
        "sentiment",
        "macro",
        "advisor",
    ]
    label_map = {
        "market_data": "Market Data",
        "technical_analysis": "Technical Analysis",
        "fundamentals": "Fundamentals",
        "sentiment": "Sentiment",
        "advisor": "Advisor",
        "macro": "Macro",
    }
    sections: list[str] = []
    for agent in ordered_agents:
        result = results.get(agent)
        if not isinstance(result, dict):
            continue
        content = normalize_content_to_text(result.get("content", "")).strip()
        if not content:
            continue
        label = label_map.get(agent, agent.replace("_", " ").title())
        sections.append(f"### {label}\n{content}")
    if not sections:
        return "No analysis content was generated."
    if len(sections) == 1:
        return sections[0].replace("### ", "", 1)
    return "Here's what I found:\n\n" + "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def _ready_agents_from_tier(
    state: SupervisorState,
    tier: set[str],
) -> list[str]:
    """Return agents in `tier` that have pending, dependency-satisfied tasks."""
    plan = state.get("plan")
    if not plan or not getattr(plan, "steps", None):
        return []
    task_status = state.get("task_status", {}) or {}
    pending_steps = [
        step for step in plan.steps
        if task_status.get(step.task_id, "pending") not in {"completed", "failed", "skipped"}
    ]
    ready: list[str] = []
    seen: set[str] = set()
    for step in pending_steps:
        if not deps_satisfied(step, task_status):
            continue
        agent = canonical_agent(step.agent)
        if agent in tier and agent not in seen:
            seen.add(agent)
            ready.append(agent)
    return ready


def route_next(state: SupervisorState):
    """Route from planner/router: dispatch Tier-1 research agents first."""
    plan = state.get("plan")
    if not plan or not getattr(plan, "steps", None):
        return "aggregator"

    task_status = state.get("task_status", {}) or {}
    all_done = all(
        task_status.get(step.task_id, "pending") in {"completed", "failed", "skipped"}
        for step in plan.steps
    )
    if all_done:
        return "aggregator"

    # Dispatch Tier-1 research agents
    ready_research = _ready_agents_from_tier(state, RESEARCH_AGENTS)
    if ready_research:
        return ready_research if len(ready_research) > 1 else ready_research[0]

    # All Tier-1 done or blocked — hand off to the research gate
    research_pending = any(
        task_status.get(step.task_id, "pending") == "pending"
        and canonical_agent(step.agent) in RESEARCH_AGENTS
        for step in plan.steps
    )
    if not research_pending:
        return "research_gate"

    return "aggregator"


def route_after_research(state: SupervisorState):
    """Route from research_gate: dispatch Tier-2 synthesis agents."""
    ready_synthesis = _ready_agents_from_tier(state, SYNTHESIS_AGENTS)
    if ready_synthesis:
        return ready_synthesis if len(ready_synthesis) > 1 else ready_synthesis[0]
    return "aggregator"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

from apps.api.agents.advisor.agent import advisor_node
from apps.api.agents.macro.agent import macro_node

workflow = StateGraph(SupervisorState)

workflow.add_node("planner", planner_node)
workflow.add_node("router", router_node)
workflow.add_node("market_data", market_data_node)
workflow.add_node("technical_analysis", technical_analysis_node)
workflow.add_node("fundamentals", fundamentals_node)
workflow.add_node("sentiment", sentiment_node)
workflow.add_node("advisor", advisor_node)
workflow.add_node("macro", macro_node)
workflow.add_node("research_gate", research_gate_node)
workflow.add_node("aggregator", aggregator_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "router")

# Tier-1 routing: planner → router → [research agents] → router (loop) → research_gate
workflow.add_conditional_edges(
    "router",
    route_next,
    {
        "market_data": "market_data",
        "fundamentals": "fundamentals",
        "sentiment": "sentiment",
        "macro": "macro",
        "research_gate": "research_gate",
        "aggregator": "aggregator",
    },
)

# After each Tier-1 agent completes, loop back to router
for agent in ("market_data", "fundamentals", "sentiment", "macro"):
    workflow.add_edge(agent, "router")

# Tier-2 routing: research_gate → [synthesis agents] → aggregator
workflow.add_conditional_edges(
    "research_gate",
    route_after_research,
    {
        "technical_analysis": "technical_analysis",
        "advisor": "advisor",
        "aggregator": "aggregator",
    },
)

# After each Tier-2 agent completes, loop back to research_gate to pick up remaining synthesis work
for agent in ("technical_analysis", "advisor"):
    workflow.add_edge(agent, "research_gate")

workflow.add_edge("aggregator", END)

# recursion_limit prevents infinite routing loops (G-2)
# recursion_limit prevents infinite routing loops (G-2).
# Pass as: graph.invoke(state, config={"recursion_limit": GRAPH_RECURSION_LIMIT})
GRAPH_RECURSION_LIMIT = 25
graph = workflow.compile()
