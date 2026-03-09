"""Retrieval node: RAG lookup against policy document corpus in Azure AI Search."""

from __future__ import annotations

import time

import structlog
from langchain_openai import AzureOpenAIEmbeddings

from riskscout.agent.state import AgentState, PolicyContext, RunStatus
from riskscout.config import get_settings
from riskscout.infrastructure.observability import emit_node_log
from riskscout.infrastructure.search import get_search_client

logger = structlog.get_logger(__name__)

TOP_K = 5


def _build_query_from_entities(entities: dict) -> str:
    """Build a semantic search query from extracted entities."""
    parts = []
    if entities.get("loan_purpose"):
        parts.append(entities["loan_purpose"])
    if entities.get("borrower_entity_type"):
        parts.append(f"{entities['borrower_entity_type']} lending policy")
    if entities.get("risk_indicators"):
        parts.extend(entities["risk_indicators"][:3])
    if entities.get("loan_amount") and entities["loan_amount"] > 5_000_000:
        parts.append("large loan concentration risk")
    if not parts:
        parts.append("financial risk assessment policy")
    return " ".join(parts)


async def retrieval_node(state: AgentState) -> dict:
    """
    Embed the entity-based query and retrieve relevant policy passages
    from Azure AI Search using vector + keyword hybrid search.
    """
    t0 = time.perf_counter()
    settings = get_settings()
    run_id = state["run_id"]

    log = logger.bind(node="retrieval_node", run_id=run_id)
    log.info("Starting policy retrieval")

    try:
        entities = state.get("extracted_entities") or {}
        query = _build_query_from_entities(entities)

        # Generate query embedding
        embedder = AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_embedding_deployment,
        )
        query_vector = await embedder.aembed_query(query)

        # Hybrid search against policy index
        search_client = get_search_client(settings.azure_search_policy_index_name)
        results = await search_client.search(
            search_text=query,
            vector_queries=[
                {
                    "kind": "vector",
                    "vector": query_vector,
                    "k_nearest_neighbors": TOP_K,
                    "fields": "content_vector",
                }
            ],
            top=TOP_K,
            select=["id", "content", "source"],
        )

        passages: list[str] = []
        source_ids: list[str] = []
        scores: list[float] = []

        async for result in results:
            passages.append(result.get("content", ""))
            source_ids.append(result.get("id", ""))
            scores.append(result.get("@search.score", 0.0))

        avg_score = sum(scores) / len(scores) if scores else 0.0
        policy_context = PolicyContext(
            passages=passages,
            source_ids=source_ids,
            retrieval_score=avg_score,
        )

        duration_ms = (time.perf_counter() - t0) * 1000
        # Embeddings don't return standard token counts via langchain — estimate
        emit_node_log("retrieval_node", run_id, duration_ms, len(query.split()), 0)
        log.info(
            "Retrieval complete",
            passages_found=len(passages),
            avg_score=round(avg_score, 3),
            duration_ms=round(duration_ms, 1),
        )

        return {
            "policy_context": policy_context.model_dump(),
            "status": RunStatus.SCORING.value,
            "node_timings": {**state.get("node_timings", {}), "retrieval_node": duration_ms},
        }

    except Exception as exc:
        log.error("Retrieval failed", error=str(exc))
        # Non-fatal: proceed with empty policy context
        return {
            "policy_context": PolicyContext().model_dump(),
            "status": RunStatus.SCORING.value,
            "error": f"retrieval_node (non-fatal): {exc}",
            "node_timings": {
                **state.get("node_timings", {}),
                "retrieval_node": (time.perf_counter() - t0) * 1000,
            },
        }
