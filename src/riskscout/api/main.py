"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from riskscout.api.routes import router
from riskscout.config import get_settings
from riskscout.infrastructure.observability import setup_telemetry
from riskscout.infrastructure.search import ensure_indexes_exist

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    settings = get_settings()
    setup_telemetry(settings.applicationinsights_connection_string or None)
    logger.info("RiskScout starting up", version="0.1.0")

    try:
        await ensure_indexes_exist()
        logger.info("Azure AI Search indexes verified")
    except Exception as exc:
        logger.warning("Could not verify search indexes", error=str(exc))

    yield

    logger.info("RiskScout shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RiskScout",
        description=(
            "Financial document intelligence agent — "
            "ingests documents, extracts entities, scores risk, "
            "and routes to approve/review/reject via LangGraph."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://risk-scout.theaiguru.dev", "https://theaiguru.dev"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "riskscout"})

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "riskscout.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
