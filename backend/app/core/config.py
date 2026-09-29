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
    # EMBEDDING_MODEL is the Azure deployment name (text-embedding-ada-002, width 1536).
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimensions: int = 1536
    embedding_similarity_gate: float = 0.72
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150
    # Background Advisor index jobs (same process). Does not block Scan Now / Scan All.
    index_concurrency: int = 1

    http_user_agent: str = (
        "ExcelsoftSalesIntelligence/0.1 (+https://example.local; research; contact=dev@example.local)"
    )
    scan_org_concurrency: int = 4
    scan_max_concurrent_sources: int = 4
    scan_max_pages_per_organization: int = 10
    scan_news_articles_per_hub: int = 5
    scan_refresh_hours: int = 0
    http_timeout_seconds: float = 15.0

    # SAM.gov Get Opportunities (DATA_SOURCES.md §2). Cap is an application safeguard.
    sam_gov_api_key: str = ""
    sam_gov_search_url: str = "https://api.sam.gov/opportunities/v2/search"
    sam_gov_daily_request_cap: int = 10
    # One shared request per scan. GSA documents `limit` up to 1000; a larger page lets one
    # request cover far more notices for local organization matching (DATA_SOURCES §2.1).
    sam_gov_search_limit: int = 1000

    # USAspending.gov API v2 (DATA_SOURCES.md §3). No API key. Fail-soft historical awards.
    usaspending_enabled: bool = True
    usaspending_max_awards_per_org: int = 8

    # Google Programmable Search (DATA_SOURCES.md §8). Peer competitors on Update. The cap is an
    # application safeguard, not Google's quota.
    google_search_api_key: str = ""
    google_search_engine_id: str = ""
    google_search_url: str = "https://www.googleapis.com/customsearch/v1"
    google_search_daily_request_cap: int = 20

    # Sales Persona live lookups. Only these official domains (plus the official website of a
    # tracked organization) may be fetched, through the same robots-respecting fetcher as scans.
    persona_live_lookup_enabled: bool = True
    persona_allowed_domains: str = (
        "honorlock.com,proctorio.com,meazurelearning.com,caveon.com,questionmark.com"
    )
    # Ceiling only; app/services/persona.py always passes an explicit, lower override per call
    # (each extra page on one host costs the mandatory 5s politeness gap — DATA_SOURCES.md §5.4).
    persona_max_live_pages_per_domain: int = 2

    # Sales Persona LLM only (does not change Advisor / scan Azure path).
    persona_gemini_api_key: str = ""
    persona_gemini_model: str = "gemini-3.8-flash"

    # APScheduler daily Scan All (TECHNICAL_PRD). Off unless explicitly enabled.
    scheduler_enabled: bool = False
    scheduler_scan_all_hour_utc: int = 6
    scheduler_scan_all_minute: int = 0

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
    def persona_domains(self) -> list[str]:
        return [
            domain.strip().lower().removeprefix("www.")
            for domain in self.persona_allowed_domains.split(",")
            if domain.strip()
        ]

    @property
    def google_search_configured(self) -> bool:
        return bool(self.google_search_api_key.strip() and self.google_search_engine_id.strip())

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
    def persona_gemini_configured(self) -> bool:
        return bool(self.persona_gemini_api_key.strip() and self.persona_gemini_model.strip())

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
