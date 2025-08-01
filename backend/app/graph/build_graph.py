# backend/app/graph/build_graph.py

from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from .router_node import router_node
from .stock_node import stock_node
from .equity_insight_node import equity_insight_node
from .advisor_node import advisor_node
from .fallback_node import fallback_node
from .synthesizer_node import synthesizer_node

class GraphState(TypedDict):
    input: str
    route: str
    output: str
    pending_tasks: List[str]
    accumulated_results: Dict[str, str]

def decide_route(state: GraphState):
    """Router decides which agent to call or synthesizer"""
    return state.get("route", "fallback")

def should_continue(state: GraphState):
    """Check if more tasks pending, if so go back to router, else synthesize"""
    pending = state.get("pending_tasks", [])
    return "router" if pending else "synthesizer"

def build_app_graph():
    builder = StateGraph(GraphState)

    builder.set_entry_point("router")

    # Add nodes
    builder.add_node("router", router_node)
    builder.add_node("stock", stock_node)
    builder.add_node("equity_insights", equity_insight_node)
    builder.add_node("advisor", advisor_node)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_node("fallback", fallback_node)

    # Router decides which agent to call
    builder.add_conditional_edges(
        "router", 
        decide_route,
        {
            "stock": "stock",
            "equity_insights": "equity_insights",
            "advisor": "advisor",
            "synthesizer": "synthesizer",
            "fallback": "fallback"
        }
    )

    # After each agent, check if more tasks needed
    builder.add_conditional_edges("stock", should_continue, {"router": "router", "synthesizer": "synthesizer"})
    builder.add_conditional_edges("equity_insights", should_continue, {"router": "router", "synthesizer": "synthesizer"})
    builder.add_conditional_edges("advisor", should_continue, {"router": "router", "synthesizer": "synthesizer"})

    # End states
    builder.add_edge("synthesizer", END)
    builder.add_edge("fallback", END)

    return builder.compile()
