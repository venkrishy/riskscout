"""Decision node: write structured decision + audit trail to Cosmos DB."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import structlog

from riskscout.agent.state import AgentState, FinalDecision, HumanReviewInput, RunStatus
from riskscout.infrastructure.cosmos import get_cosmos_client
from riskscout.infrastructure.observability import emit_node_log

logger = structlog.get_logger(__name__)


async def decision_node(state: AgentState) -> dict[str, Any]:
    """
    Assemble the final structured decision and persist it to Cosmos DB.
    Builds a full audit trail from node timings and intermediate outputs.
    """
    t0 = time.perf_counter()
    run_id = state["run_id"]
    document_id = state["document_id"]

    log = logger.bind(node="decision_node", run_id=run_id)
    log.info("Writing final decision")

    try:
        risk_score_data = state.get("risk_score") or {}
        entities = state.get("extracted_entities") or {}
        routing_decision = state.get("routing_decision", "review")
        human_review_data = state.get("human_review")

        # Determine final status based on routing decision
        if routing_decision == "approve":
            final_status = RunStatus.APPROVED
        elif routing_decision == "reject":
            final_status = RunStatus.REJECTED
        else:
            final_status = RunStatus.REVIEW_COMPLETE

        human_review = None
        if human_review_data:
            try:
                human_review = HumanReviewInput(**human_review_data)
            except Exception:
                pass

        audit_trail = [
            {
                "step": node_name,
                "duration_ms": round(duration_ms, 1),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            for node_name, duration_ms in state.get("node_timings", {}).items()
        ]

        final_decision = FinalDecision(
            run_id=run_id,
            document_id=document_id,
            routing_decision=routing_decision,  # type: ignore[arg-type]
            risk_score=risk_score_data.get("score", 0),
            entities=entities,
            reasoning=risk_score_data.get("reasoning", ""),
            human_review=human_review,
            audit_trail=audit_trail,
        )

        # Persist to Cosmos DB
        cosmos_client = await get_cosmos_client()
        item = {
            "id": run_id,
            "partitionKey": run_id,
            **final_decision.model_dump(mode="json"),
        }
        await cosmos_client.upsert_item(item)

        duration_ms = (time.perf_counter() - t0) * 1000
        emit_node_log("decision_node", run_id, duration_ms, 0, 0)
        log.info(
            "Decision persisted",
            decision=routing_decision,
            score=risk_score_data.get("score"),
            duration_ms=round(duration_ms, 1),
        )

        return {
            "final_decision": final_decision.model_dump(mode="json"),
            "status": final_status.value,
            "node_timings": {**state.get("node_timings", {}), "decision_node": duration_ms},
        }

    except Exception as exc:
        log.error("Decision node failed", error=str(exc))
        return {
            "status": RunStatus.FAILED.value,
            "error": f"decision_node: {exc}",
        }
