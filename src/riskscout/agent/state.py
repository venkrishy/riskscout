"""LangGraph state definitions and Pydantic models for RiskScout."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    EXTRACTING = "extracting"
    RETRIEVING = "retrieving"
    SCORING = "scoring"
    AWAITING_REVIEW = "awaiting_review"
    DECIDING = "deciding"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW_COMPLETE = "review_complete"
    FAILED = "failed"


class RoutingDecision(str, Enum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Pydantic domain models
# ---------------------------------------------------------------------------


class ExtractedEntities(BaseModel):
    """Structured entities extracted from the financial document."""

    borrower_name: str | None = None
    borrower_entity_type: str | None = None  # individual / corporation / LLC
    loan_amount: float | None = None
    loan_currency: str = "USD"
    loan_purpose: str | None = None
    collateral_description: str | None = None
    collateral_value: float | None = None
    annual_revenue: float | None = None
    net_income: float | None = None
    debt_to_income_ratio: float | None = None
    credit_score: int | None = None
    years_in_business: float | None = None
    document_date: str | None = None
    counterparties: list[str] = Field(default_factory=list)
    risk_indicators: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    raw_extraction: dict[str, Any] = Field(default_factory=dict)


class RiskScore(BaseModel):
    """Risk assessment output from the scoring node."""

    score: int = Field(..., ge=0, le=100, description="Risk score 0 (low risk) to 100 (high risk)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    key_risk_factors: list[str] = Field(default_factory=list)
    mitigating_factors: list[str] = Field(default_factory=list)
    policy_references: list[str] = Field(default_factory=list)


class HumanReviewInput(BaseModel):
    """Payload submitted by a human reviewer."""

    reviewer_id: str
    override_decision: RoutingDecision
    notes: str = ""
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FinalDecision(BaseModel):
    """Structured decision written to Cosmos DB."""

    run_id: str
    document_id: str
    routing_decision: RoutingDecision
    risk_score: int
    entities: dict[str, Any]
    reasoning: str
    human_review: HumanReviewInput | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    """A single text chunk ready for embedding and indexing."""

    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    run_id: str
    content: str
    page_number: int | None = None
    chunk_index: int = 0


class PolicyContext(BaseModel):
    """Retrieved policy passages relevant to the current document."""

    passages: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    retrieval_score: float = 0.0


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    """Full state threaded through all nodes of the RiskScout graph."""

    # Identity
    run_id: str
    document_id: str

    # Raw input
    document_bytes: bytes | None
    document_filename: str
    document_text: str

    # Processing outputs
    chunks: list[dict[str, Any]]
    extracted_entities: dict[str, Any] | None
    policy_context: dict[str, Any] | None
    risk_score: dict[str, Any] | None

    # Routing
    routing_decision: str | None  # RoutingDecision value

    # Human review
    human_review: dict[str, Any] | None

    # Final output
    final_decision: dict[str, Any] | None

    # Status tracking
    status: str  # RunStatus value
    error: str | None

    # Observability
    node_timings: dict[str, float]

    # Message history (for LangGraph interrupt/resume pattern)
    messages: Annotated[list[Any], add_messages]
