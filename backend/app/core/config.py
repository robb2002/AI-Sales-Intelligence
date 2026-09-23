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
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: int = 60
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"

    http_user_agent: str = (
        "ExcelsoftSalesIntelligence/0.1 (+https://example.local; research; contact=dev@example.local)"
    )
    scan_org_concurrency: int = 2
    url_validation_timeout_seconds: float = 20.0

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
