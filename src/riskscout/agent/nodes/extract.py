"""Extract node: LLM call to extract structured entities from the document."""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr, ValidationError

from riskscout.agent.state import AgentState, ExtractedEntities, RunStatus
from riskscout.config import get_settings
from riskscout.infrastructure.observability import emit_node_log

logger = structlog.get_logger(__name__)

EXTRACT_SYSTEM_PROMPT = """\
You are a financial document analyst. Extract key entities from the provided document text.
Return ONLY valid JSON matching the schema. Use null for missing fields.

Required schema:
{
  "borrower_name": string | null,
  "borrower_entity_type": "individual" | "corporation" | "LLC" | "partnership" | null,
  "loan_amount": number | null,
  "loan_currency": string,
  "loan_purpose": string | null,
  "collateral_description": string | null,
  "collateral_value": number | null,
  "annual_revenue": number | null,
  "net_income": number | null,
  "debt_to_income_ratio": number | null,
  "credit_score": integer | null,
  "years_in_business": number | null,
  "document_date": "YYYY-MM-DD" | null,
  "counterparties": [string],
  "risk_indicators": [string],
  "key_terms": [string]
}

Risk indicators include: late payments, defaults, liens, judgments, high leverage,
concentration risk, covenant violations, related-party transactions, etc.
"""


async def extract_node(state: AgentState) -> dict[str, Any]:
    """
    Call Azure OpenAI to extract structured financial entities from document text.
    Counts tokens and emits an observability log.
    """
    t0 = time.perf_counter()
    settings = get_settings()
    run_id = state["run_id"]

    log = logger.bind(node="extract_node", run_id=run_id)
    log.info("Starting entity extraction")

    try:
        llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=SecretStr(settings.azure_openai_api_key),
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_chat_deployment,
            temperature=0,
            model_kwargs={"max_tokens": 2000},
        )

        # Truncate document text to avoid token overflow (~12k chars ~= 3k tokens)
        doc_text = state["document_text"][:12000]

        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract entities from this financial document:\n\n{doc_text}",
            },
        ]

        response = await llm.ainvoke(messages)
        content = response.content
        usage = response.response_metadata.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Parse JSON response
        assert isinstance(content, str), f"Unexpected LLM content type: {type(content)}"
        json_str = content.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]

        raw_data = json.loads(json_str)

        try:
            entities = ExtractedEntities(**raw_data)
        except ValidationError:
            entities = ExtractedEntities(raw_extraction=raw_data)

        duration_ms = (time.perf_counter() - t0) * 1000
        emit_node_log("extract_node", run_id, duration_ms, input_tokens, output_tokens)
        log.info(
            "Extraction complete",
            borrower=entities.borrower_name,
            loan_amount=entities.loan_amount,
            risk_indicators=len(entities.risk_indicators),
            duration_ms=round(duration_ms, 1),
        )

        return {
            "extracted_entities": entities.model_dump(),
            "status": RunStatus.RETRIEVING.value,
            "node_timings": {**state.get("node_timings", {}), "extract_node": duration_ms},
        }

    except Exception as exc:
        log.error("Extraction failed", error=str(exc))
        return {
            "status": RunStatus.FAILED.value,
            "error": f"extract_node: {exc}",
        }
