"""API route handlers for RiskScout."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from pydantic import BaseModel

from riskscout.agent.graph import get_graph
from riskscout.agent.state import AgentState, RunStatus
from riskscout.infrastructure.cosmos import CosmosRunStore, get_cosmos_client

router = APIRouter()
logger = structlog.get_logger(__name__)

# In-process run state cache (supplements Cosmos for low-latency status reads)
_run_cache: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AnalyzeResponse(BaseModel):
    run_id: str
    document_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    run_id: str
    status: str
    routing_decision: str | None
    risk_score: int | None
    error: str | None


class ReviewRequest(BaseModel):
    reviewer_id: str
    override_decision: str  # "approve" | "reject"
    notes: str = ""


class ReviewResponse(BaseModel):
    run_id: str
    status: str
    message: str


class DecisionResponse(BaseModel):
    run_id: str
    document_id: str
    routing_decision: str
    risk_score: int
    reasoning: str
    entities: dict[str, Any]
    human_review: dict[str, Any] | None
    audit_trail: list[dict[str, Any]]
    decided_at: str


# ---------------------------------------------------------------------------
# Background graph runner
# ---------------------------------------------------------------------------


async def _run_graph(run_id: str, initial_state: AgentState) -> None:
    """Execute the LangGraph pipeline in the background."""
    graph = get_graph()
    config = {"configurable": {"thread_id": run_id}}

    try:
        async for event in graph.astream(initial_state, config=config):
            # Update in-memory cache with latest state
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    _run_cache[run_id] = {**_run_cache.get(run_id, {}), **node_output}

        # Check if graph paused at interrupt (human review)
        snapshot = graph.get_state(config)
        if snapshot.next and "human_review_node" in snapshot.next:
            _run_cache[run_id]["status"] = RunStatus.AWAITING_REVIEW.value
            logger.info("Graph paused for human review", run_id=run_id)

    except Exception as exc:
        logger.error("Graph execution error", run_id=run_id, error=str(exc))
        _run_cache[run_id] = {
            **_run_cache.get(run_id, {}),
            "status": RunStatus.FAILED.value,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> AnalyzeResponse:
    """
    Upload a financial document (PDF or text) and start an agent run.
    Returns a run_id for status polling.
    """
    run_id = str(uuid4())
    document_id = str(uuid4())

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    initial_state: AgentState = {
        "run_id": run_id,
        "document_id": document_id,
        "document_bytes": contents,
        "document_filename": file.filename or "document",
        "document_text": "",
        "chunks": [],
        "extracted_entities": None,
        "policy_context": None,
        "risk_score": None,
        "routing_decision": None,
        "human_review": None,
        "final_decision": None,
        "status": RunStatus.INGESTING.value,
        "error": None,
        "node_timings": {},
        "messages": [],
    }

    _run_cache[run_id] = {
        "run_id": run_id,
        "document_id": document_id,
        "status": RunStatus.INGESTING.value,
    }

    background_tasks.add_task(_run_graph, run_id, initial_state)

    logger.info("Analysis started", run_id=run_id, filename=file.filename)
    return AnalyzeResponse(
        run_id=run_id,
        document_id=document_id,
        status=RunStatus.INGESTING.value,
        message="Document accepted. Poll /status/{run_id} for progress.",
    )


@router.get("/status/{run_id}", response_model=StatusResponse)
async def get_status(run_id: str) -> StatusResponse:
    """Return current run status and routing decision (if available)."""
    state = _run_cache.get(run_id)
    if not state:
        # Fall back to Cosmos
        container = await get_cosmos_client()
        store = CosmosRunStore(container)
        record = await store.get_run(run_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        state = record

    risk_score_data = state.get("risk_score") or {}
    return StatusResponse(
        run_id=run_id,
        status=state.get("status", RunStatus.PENDING.value),
        routing_decision=state.get("routing_decision"),
        risk_score=risk_score_data.get("score"),
        error=state.get("error"),
    )


@router.post("/review/{run_id}", response_model=ReviewResponse)
async def submit_review(run_id: str, body: ReviewRequest) -> ReviewResponse:
    """
    Submit a human review decision to resume a paused graph.
    Only valid when run status is awaiting_review.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": run_id}}

    snapshot = graph.get_state(config)
    if not snapshot or not snapshot.next:
        state = _run_cache.get(run_id, {})
        current_status = state.get("status", "unknown")
        raise HTTPException(
            status_code=409,
            detail=f"Run {run_id} is not awaiting review (status: {current_status})",
        )

    review_payload = {
        "reviewer_id": body.reviewer_id,
        "override_decision": body.override_decision,
        "notes": body.notes,
    }

    # Resume graph by updating state with human decision
    graph.update_state(config, {"human_review": review_payload}, as_node="human_review_node")

    # Continue execution in background
    async def _resume() -> None:
        try:
            async for event in graph.astream(None, config=config):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        _run_cache[run_id] = {**_run_cache.get(run_id, {}), **node_output}
        except Exception as exc:
            logger.error("Graph resume error", run_id=run_id, error=str(exc))
            _run_cache[run_id]["status"] = RunStatus.FAILED.value

    asyncio.create_task(_resume())

    logger.info("Human review submitted", run_id=run_id, decision=body.override_decision)
    return ReviewResponse(
        run_id=run_id,
        status=RunStatus.DECIDING.value,
        message="Review accepted. Graph resumed.",
    )


@router.get("/decision/{run_id}", response_model=DecisionResponse)
async def get_decision(run_id: str) -> DecisionResponse:
    """Return the final structured decision for a completed run."""
    state = _run_cache.get(run_id, {})
    final = state.get("final_decision")

    if not final:
        # Try Cosmos DB
        container = await get_cosmos_client()
        store = CosmosRunStore(container)
        record = await store.get_run(run_id)
        if record and record.get("final_decision"):
            final = record["final_decision"]
        elif record and record.get("routing_decision"):
            # Decision written directly (not nested)
            final = record

    if not final:
        current_status = state.get("status", "unknown")
        raise HTTPException(
            status_code=404,
            detail=f"Decision not yet available for run {run_id} (status: {current_status})",
        )

    return DecisionResponse(
        run_id=final.get("run_id", run_id),
        document_id=final.get("document_id", ""),
        routing_decision=final.get("routing_decision", ""),
        risk_score=final.get("risk_score", 0),
        reasoning=final.get("reasoning", ""),
        entities=final.get("entities", {}),
        human_review=final.get("human_review"),
        audit_trail=final.get("audit_trail", []),
        decided_at=final.get("decided_at", ""),
    )
