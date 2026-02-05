# src/graph/graph.py - TAM DOSYA (linear yerine loop'lu versiyon)

"""
graph.py
--------
LangGraph StateGraph'i build ve compile eder.

Topology:
    START -> analyst -> critic --(retry)--> retry_node -> analyst  (loop)
                            |
                            +-----------(fixer)-------> fixer -> END
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from langgraph.graph import StateGraph, END

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

from src.graph.state import PipelineState
from src.graph.nodes.analyst import analyst_node
from src.graph.nodes.critic  import critic_node
from src.graph.nodes.fixer   import fixer_node
from src.graph.nodes.retry   import retry_node
from src.graph.router        import critic_router


def build_graph() -> "CompiledStateGraph":
    """
    Graph'i olustur ve compile et.

    Returns:
        Compiled LangGraph — .invoke() ile calistirildı.
    """
    graph = StateGraph(PipelineState)

    # ── Nodes ──────────────────────────────────────────
    graph.add_node("analyst",    analyst_node)
    graph.add_node("critic",     critic_node)
    graph.add_node("retry",      retry_node)
    graph.add_node("fixer",      fixer_node)

    # ── Edges ──────────────────────────────────────────
    graph.set_entry_point("analyst")                  # START -> analyst

    graph.add_edge("analyst", "critic")               # analyst -> critic (her zaman)

    graph.add_conditional_edges(                      # critic -> router karar
        "critic",
        critic_router,
        {
            "retry": "retry",                         # not approved + retry left
            "fixer": "fixer",                         # approved OR max retry
        },
    )

    graph.add_edge("retry", "analyst")                # retry -> analyst (loop back)
    graph.add_edge("fixer", END)                      # fixer -> END

    return graph.compile()