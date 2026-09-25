from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "production"] = "local"
    log_level: str = "INFO"
    database_url: str
    clerk_secret_key: str
    cors_allowed_origins: str

    llm_provider: str = "azure_openai"
    llm_model: str = "interns-gpt-4.1"
    llm_api_key: str = ""
    llm_timeout_seconds: int = 60
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"

    # Azure embedding deployment (Advisor RAG). Same resource/key as chat LLM.
    # Deploy text-embedding-3-small; EMBEDDING_MODEL is that deployment name.
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_similarity_gate: float = 0.72
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150

    http_user_agent: str = (
        "ExcelsoftSalesIntelligence/0.1 (+https://example.local; research; contact=dev@example.local)"
    )
    scan_org_concurrency: int = 2
    scan_max_concurrent_sources: int = 4
    scan_max_pages_per_organization: int = 10
    scan_news_articles_per_hub: int = 5
    scan_refresh_hours: int = 0
    http_timeout_seconds: float = 15.0

    # SAM.gov Get Opportunities (DATA_SOURCES.md §2). Cap is an application safeguard.
    sam_gov_api_key: str = ""
    sam_gov_search_url: str = "https://api.sam.gov/opportunities/v2/search"
    sam_gov_daily_request_cap: int = 10
    sam_gov_search_limit: int = 25

    @field_validator("database_url")
    @classmethod
    def use_asyncpg_driver(cls, value: str) -> str:
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix):]
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider == "azure_openai":
            return bool(
                self.llm_api_key.strip()
                and self.azure_openai_endpoint.strip()
                and self.llm_model.strip()
            )
        return bool(self.llm_api_key.strip() and self.llm_model.strip())

    @property
    def embedding_configured(self) -> bool:
        return bool(
            self.llm_api_key.strip()
            and self.azure_openai_endpoint.strip()
            and self.embedding_model.strip()
            and self.embedding_dimensions > 0
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
