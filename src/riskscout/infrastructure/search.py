"""Azure AI Search client — document corpus and policy index."""

from __future__ import annotations

from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

from riskscout.config import get_settings


@lru_cache(maxsize=8)
def get_search_client(index_name: str) -> SearchClient:
    """Return an async SearchClient for the given index."""
    settings = get_settings()
    credential = AzureKeyCredential(settings.azure_search_api_key)
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=index_name,
        credential=credential,
    )


async def ensure_indexes_exist() -> None:
    """
    Create the document and policy indexes if they don't exist.
    Indexes support both keyword and vector search (hybrid).
    """
    from azure.search.documents.indexes.aio import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )

    settings = get_settings()
    credential = AzureKeyCredential(settings.azure_search_api_key)
    index_client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint, credential=credential
    )

    for index_name in [settings.azure_search_index_name, settings.azure_search_policy_index_name]:
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="run_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,  # text-embedding-3-large
                vector_search_profile_name="hnsw-profile",
            ),
        ]

        vector_search = VectorSearch(
            profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw")],
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
        )

        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

        try:
            await index_client.create_index(index)
        except Exception:
            pass  # Already exists
