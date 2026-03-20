"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_api_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_api_version: str = Field(default="2024-02-01")
    azure_openai_chat_deployment: str = Field(
        default="gpt-4o", description="Chat model deployment name"
    )
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-3-large", description="Embedding model deployment name"
    )

    # Azure AI Search
    azure_search_endpoint: str = Field(..., description="Azure AI Search service endpoint")
    azure_search_api_key: str = Field(..., description="Azure AI Search admin key")
    azure_search_index_name: str = Field(default="riskscout-documents")
    azure_search_policy_index_name: str = Field(default="riskscout-policy")

    # Azure Cosmos DB
    cosmos_endpoint: str = Field(..., description="Cosmos DB account endpoint")
    cosmos_key: str = Field(..., description="Cosmos DB account key")
    cosmos_database: str = Field(default="riskscout")
    cosmos_container: str = Field(default="runs")

    # Application Insights
    applicationinsights_connection_string: str = Field(
        default="", description="App Insights connection string (optional)"
    )

    # Risk routing thresholds
    approve_threshold: int = Field(default=80, ge=0, le=100)
    reject_threshold: int = Field(default=40, ge=0, le=100)

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    # Chunking
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
