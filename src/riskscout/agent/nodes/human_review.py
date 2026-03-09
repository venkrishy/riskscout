"""Human review node: interrupt/checkpoint for human-in-the-loop decisioning."""

from __future__ import annotations

import time

import structlog
from langgraph.types import interrupt

from riskscout.agent.state import AgentState, HumanReviewInput, RunStatus
from riskscout.infrastructure.observability import emit_node_log

logger = structlog.get_logger(__name__)


async def human_review_node(state: AgentState) -> dict:
    """
    Pause graph execution using LangGraph's interrupt() mechanism.
    The graph is resumed by POSTing to /review/{run_id} with a HumanReviewInput payload.
    The interrupt value surfaces the current risk assessment for the reviewer.
    """
    t0 = time.perf_counter()
    run_id = state["run_id"]

    log = logger.bind(node="human_review_node", run_id=run_id)
    log.info("Pausing for human review")

    risk_score_data = state.get("risk_score") or {}
    entities = state.get("extracted_entities") or {}

    # interrupt() suspends graph execution and returns this dict to the caller.
    # When resumed, `review_payload` contains the human reviewer's response.
    review_payload: dict = interrupt(
        {
            "message": "Human review required. Submit decision via POST /review/{run_id}.",
            "run_id": run_id,
            "risk_score": risk_score_data.get("score"),
            "reasoning": risk_score_data.get("reasoning"),
            "borrower_name": entities.get("borrower_name"),
            "loan_amount": entities.get("loan_amount"),
            "risk_factors": risk_score_data.get("key_risk_factors", []),
        }
    )

    # After resume, review_payload contains the human's decision dict
    try:
        human_review = HumanReviewInput(**review_payload)
    except Exception as exc:
        log.error("Invalid human review payload", error=str(exc))
        human_review = HumanReviewInput(
            reviewer_id="system",
            override_decision=state.get("routing_decision", "review"),  # type: ignore[arg-type]
            notes=f"Auto-resumed with error: {exc}",
        )

    duration_ms = (time.perf_counter() - t0) * 1000
    emit_node_log("human_review_node", run_id, duration_ms, 0, 0)
    log.info(
        "Human review received",
        reviewer=human_review.reviewer_id,
        override=human_review.override_decision.value,
    )

    return {
        "human_review": human_review.model_dump(mode="json"),
        "routing_decision": human_review.override_decision.value,
        "status": RunStatus.DECIDING.value,
        "node_timings": {**state.get("node_timings", {}), "human_review_node": duration_ms},
    }
