"""Azure Cosmos DB client — stores agent run history and final decisions."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from azure.cosmos.aio import ContainerProxy, CosmosClient

from riskscout.config import get_settings


@lru_cache(maxsize=1)
def _get_cosmos_client_instance() -> CosmosClient:
    settings = get_settings()
    return CosmosClient(url=settings.cosmos_endpoint, credential=settings.cosmos_key)


async def get_cosmos_client() -> ContainerProxy:
    """Return the Cosmos DB container proxy for run records."""
    settings = get_settings()
    client = _get_cosmos_client_instance()
    database = client.get_database_client(settings.cosmos_database)
    return database.get_container_client(settings.cosmos_container)


class CosmosRunStore:
    """High-level helper for persisting and reading run records."""

    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    async def upsert_run(self, run_id: str, data: dict[str, Any]) -> None:
        item = {"id": run_id, "partitionKey": run_id, **data}
        await self._container.upsert_item(item)

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        try:
            return await self._container.read_item(item=run_id, partition_key=run_id)
        except Exception:
            return None

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        query = f"SELECT TOP {limit} * FROM c ORDER BY c._ts DESC"
        items = []
        async for item in self._container.query_items(query=query):
            items.append(item)
        return items
