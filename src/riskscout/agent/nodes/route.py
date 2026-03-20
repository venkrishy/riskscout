"""Route node: conditional edge determining approve / review / reject."""

from __future__ import annotations

import time
from typing import Any

import structlog

from riskscout.agent.state import AgentState, RoutingDecision, RunStatus
from riskscout.config import get_settings
from riskscout.infrastructure.observability import emit_node_log

logger = structlog.get_logger(__name__)


async def route_node(state: AgentState) -> dict[str, Any]:
    """
    Apply configurable thresholds to the risk score and set routing_decision.
    This node is synchronous in logic; the actual conditional edge is wired in graph.py.
    """
    t0 = time.perf_counter()
    settings = get_settings()
    run_id = state["run_id"]

    log = logger.bind(node="route_node", run_id=run_id)

    risk_score_data = state.get("risk_score") or {}
    score = risk_score_data.get("score", 50)

    if score >= settings.approve_threshold:
        decision = RoutingDecision.REJECT  # High score = high risk = reject
        next_status = RunStatus.DECIDING
    elif score < settings.reject_threshold:
        decision = RoutingDecision.APPROVE  # Low score = low risk = approve
        next_status = RunStatus.DECIDING
    else:
        decision = RoutingDecision.REVIEW
        next_status = RunStatus.AWAITING_REVIEW

    duration_ms = (time.perf_counter() - t0) * 1000
    emit_node_log("route_node", run_id, duration_ms, 0, 0)
    log.info(
        "Routing decision",
        score=score,
        decision=decision.value,
        approve_threshold=settings.approve_threshold,
        reject_threshold=settings.reject_threshold,
    )

    return {
        "routing_decision": decision.value,
        "status": next_status.value,
        "node_timings": {**state.get("node_timings", {}), "route_node": duration_ms},
    }


def get_routing_decision(state: AgentState) -> str:
    """
    Conditional edge function for LangGraph — returns the next node name
    based on routing_decision in state.
    """
    decision = state.get("routing_decision")
    if decision == RoutingDecision.REVIEW.value:
        return "human_review_node"
    return "decision_node"
