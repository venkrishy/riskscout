"""Score node: LLM call to produce a risk score (0-100) with reasoning."""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr, ValidationError

from riskscout.agent.state import AgentState, RiskScore, RunStatus
from riskscout.config import get_settings
from riskscout.infrastructure.observability import emit_node_log

logger = structlog.get_logger(__name__)

SCORE_SYSTEM_PROMPT = """\
You are a senior credit risk analyst at a financial institution. Your task is to produce
a structured risk score for a financial document based on:

1. Extracted entities from the document
2. Relevant policy passages retrieved from the policy corpus

Risk score interpretation:
- 80-100: HIGH RISK — likely reject
- 40-79:  MODERATE RISK — requires human review
- 0-39:   LOW RISK — likely approve

Return ONLY valid JSON with this schema:
{
  "score": integer (0-100),
  "confidence": float (0.0-1.0),
  "reasoning": "2-3 sentence explanation of score rationale",
  "key_risk_factors": ["factor1", "factor2", ...],
  "mitigating_factors": ["factor1", "factor2", ...],
  "policy_references": ["policy excerpt 1", ...]
}

Be objective, cite specific numbers from the entities, and reference policy passages where relevant.
"""


async def score_node(state: AgentState) -> dict[str, Any]:
    """
    Call Azure OpenAI to produce a risk score based on entities and policy context.
    """
    t0 = time.perf_counter()
    settings = get_settings()
    run_id = state["run_id"]

    log = logger.bind(node="score_node", run_id=run_id)
    log.info("Starting risk scoring")

    try:
        llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=SecretStr(settings.azure_openai_api_key),
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_chat_deployment,
            temperature=0,
            model_kwargs={"max_tokens": 1500},
        )

        entities = state.get("extracted_entities") or {}
        policy_ctx = state.get("policy_context") or {}
        policy_passages = policy_ctx.get("passages", [])

        policy_text = (
            "\n\n".join(f"[Policy {i + 1}]: {p}" for i, p in enumerate(policy_passages[:3]))
            if policy_passages
            else "No policy passages retrieved."
        )

        user_content = f"""
EXTRACTED ENTITIES:
{json.dumps(entities, indent=2, default=str)}

RELEVANT POLICY PASSAGES:
{policy_text}

Please score this document's risk level.
"""

        messages = [
            {"role": "system", "content": SCORE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        response = await llm.ainvoke(messages)
        content = response.content
        usage = response.response_metadata.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        assert isinstance(content, str), f"Unexpected LLM content type: {type(content)}"
        json_str = content.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]

        raw_data = json.loads(json_str)

        try:
            risk_score = RiskScore(**raw_data)
        except ValidationError as e:
            log.warning("RiskScore validation partial", error=str(e))
            risk_score = RiskScore(
                score=max(0, min(100, int(raw_data.get("score", 50)))),
                confidence=float(raw_data.get("confidence", 0.5)),
                reasoning=raw_data.get("reasoning", "Score computed with partial validation."),
                key_risk_factors=raw_data.get("key_risk_factors", []),
                mitigating_factors=raw_data.get("mitigating_factors", []),
                policy_references=raw_data.get("policy_references", []),
            )

        duration_ms = (time.perf_counter() - t0) * 1000
        emit_node_log("score_node", run_id, duration_ms, input_tokens, output_tokens)
        log.info(
            "Scoring complete",
            score=risk_score.score,
            confidence=risk_score.confidence,
            duration_ms=round(duration_ms, 1),
        )

        return {
            "risk_score": risk_score.model_dump(),
            "status": RunStatus.SCORING.value,
            "node_timings": {**state.get("node_timings", {}), "score_node": duration_ms},
        }

    except Exception as exc:
        log.error("Scoring failed", error=str(exc))
        return {
            "status": RunStatus.FAILED.value,
            "error": f"score_node: {exc}",
        }
