"""Ingest node: parse PDF/text, chunk, and store to Azure AI Search."""

from __future__ import annotations

import time
from io import BytesIO
from uuid import uuid4

import structlog
from pypdf import PdfReader

from riskscout.agent.state import AgentState, DocumentChunk, RunStatus
from riskscout.config import get_settings
from riskscout.infrastructure.observability import emit_node_log
from riskscout.infrastructure.search import get_search_client

logger = structlog.get_logger(__name__)


def _extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


async def ingest_node(state: AgentState) -> dict:
    """
    Parse the uploaded document, chunk it, and index chunks in Azure AI Search.
    Emits a structured observability log on completion.
    """
    t0 = time.perf_counter()
    settings = get_settings()
    run_id = state["run_id"]
    document_id = state["document_id"]

    log = logger.bind(node="ingest_node", run_id=run_id)
    log.info("Starting document ingestion", filename=state["document_filename"])

    try:
        # --- Text extraction ---
        raw = state.get("document_bytes") or b""
        filename = state.get("document_filename", "")

        if filename.lower().endswith(".pdf") and raw:
            document_text = _extract_text_from_pdf(raw)
        elif raw:
            document_text = raw.decode("utf-8", errors="replace")
        else:
            document_text = state.get("document_text", "")

        if not document_text.strip():
            raise ValueError("Document produced no extractable text")

        # --- Chunking ---
        raw_chunks = _chunk_text(document_text, settings.chunk_size, settings.chunk_overlap)
        chunks = [
            DocumentChunk(
                document_id=document_id,
                run_id=run_id,
                content=chunk,
                chunk_index=i,
            )
            for i, chunk in enumerate(raw_chunks)
        ]

        # --- Index to Azure AI Search ---
        search_client = get_search_client(settings.azure_search_index_name)
        documents_to_index = [
            {
                "id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "run_id": chunk.run_id,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]
        await search_client.upload_documents(documents_to_index)

        duration_ms = (time.perf_counter() - t0) * 1000
        emit_node_log("ingest_node", run_id, duration_ms, 0, 0)
        log.info("Ingestion complete", chunks=len(chunks), duration_ms=round(duration_ms, 1))

        return {
            "document_text": document_text,
            "chunks": [c.model_dump() for c in chunks],
            "status": RunStatus.EXTRACTING.value,
            "node_timings": {**state.get("node_timings", {}), "ingest_node": duration_ms},
        }

    except Exception as exc:
        log.error("Ingestion failed", error=str(exc))
        return {
            "status": RunStatus.FAILED.value,
            "error": f"ingest_node: {exc}",
        }
