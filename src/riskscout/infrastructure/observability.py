"""OpenTelemetry + Azure Application Insights observability setup."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_telemetry_initialized = False


def setup_telemetry(connection_string: str | None = None) -> None:
    """
    Initialize OpenTelemetry with Azure Monitor exporter.
    Falls back to console-only logging if no connection string is provided.
    """
    global _telemetry_initialized
    if _telemetry_initialized:
        return

    if connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=connection_string)
            logger.info("Azure Monitor telemetry configured")
        except ImportError:
            logger.warning("azure-monitor-opentelemetry not installed; skipping App Insights")
    else:
        logger.info("No App Insights connection string — using console logging only")

    # Configure structlog for JSON output
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    _telemetry_initialized = True


def emit_node_log(
    node: str,
    run_id: str,
    duration_ms: float,
    input_tokens: int,
    output_tokens: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Emit a structured log entry for a completed LangGraph node.
    Format: { node, run_id, duration_ms, input_tokens, output_tokens, timestamp }
    """
    record: dict[str, Any] = {
        "node": node,
        "run_id": run_id,
        "duration_ms": round(duration_ms, 2),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if extra:
        record.update(extra)

    # structlog emits this as JSON; Application Insights picks it up via OTel
    logger.info("node_complete", **record)
