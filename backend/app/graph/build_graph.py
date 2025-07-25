# backend/app/graph/build_graph.py

from typing import TypedDict
from langgraph.graph import StateGraph, END
from .router_node import router_node
from .stock_node import stock_node
from .equity_insight_node import equity_insight_node
from .fallback_node import fallback_node

class GraphState(TypedDict):
    input: str
    route: str
    output: str

def decide_route(state: GraphState):
    """Condition function to decide routing based on router output"""
    return state.get("route", "fallback")

def build_app_graph():
    builder = StateGraph(GraphState)

    builder.set_entry_point("router")

    builder.add_node("router", router_node)
    builder.add_node("stock", stock_node)
    builder.add_node("equity_insights", equity_insight_node)
    builder.add_node("fallback", fallback_node)

    builder.add_conditional_edges(
        "router", 
        decide_route,
        {
            "stock": "stock",
            "equity_insights": "equity_insights",
            "fallback": "fallback"
        }
    )

    builder.add_edge("stock", END)
    builder.add_edge("equity_insights", END)
    builder.add_edge("fallback", END)

    return builder.compile()
