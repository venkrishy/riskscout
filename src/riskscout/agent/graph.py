"""LangGraph StateGraph assembly for RiskScout."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from riskscout.agent.nodes.decision import decision_node
from riskscout.agent.nodes.extract import extract_node
from riskscout.agent.nodes.human_review import human_review_node
from riskscout.agent.nodes.ingest import ingest_node
from riskscout.agent.nodes.retrieval import retrieval_node
from riskscout.agent.nodes.route import get_routing_decision, route_node
from riskscout.agent.nodes.score import score_node
from riskscout.agent.state import AgentState


def build_graph() -> StateGraph:
    """
    Construct and compile the RiskScout StateGraph.

    Graph topology:
        START
          → ingest_node
          → extract_node
          → retrieval_node
          → score_node
          → route_node ─── (conditional) ─── human_review_node ──→ decision_node → END
                       \\                                                          /
                        ──────────────────────────────────────────────────────────

    The human_review_node uses LangGraph's interrupt() to pause execution.
    MemorySaver provides in-process checkpointing for interrupt/resume support.
    """
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("ingest_node", ingest_node)
    builder.add_node("extract_node", extract_node)
    builder.add_node("retrieval_node", retrieval_node)
    builder.add_node("score_node", score_node)
    builder.add_node("route_node", route_node)
    builder.add_node("human_review_node", human_review_node)
    builder.add_node("decision_node", decision_node)

    # Linear edges
    builder.add_edge(START, "ingest_node")
    builder.add_edge("ingest_node", "extract_node")
    builder.add_edge("extract_node", "retrieval_node")
    builder.add_edge("retrieval_node", "score_node")
    builder.add_edge("score_node", "route_node")

    # Conditional edge from route_node
    builder.add_conditional_edges(
        "route_node",
        get_routing_decision,
        {
            "human_review_node": "human_review_node",
            "decision_node": "decision_node",
        },
    )

    # Human review always leads to decision
    builder.add_edge("human_review_node", "decision_node")
    builder.add_edge("decision_node", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer, interrupt_before=["human_review_node"])


# Singleton compiled graph
_graph: StateGraph | None = None


def get_graph() -> StateGraph:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
