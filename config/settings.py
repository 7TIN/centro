# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     # LLM Configuration
#     anthropic_api_key: str
#     openai_api_key: str
#     primary_model: str = "claude-sonnet-4-20250514"
#     fallback_model: str = "gpt-4"
    
#     # Vector DB
#     pinecone_api_key: str
#     pinecone_index: str = "personx-knowledge"
#     embedding_model: str = "text-embedding-3-small"
    
#     # Database
#     database_url: str
#     redis_url: str
    
#     # App Settings
#     max_context_tokens: int = 8000
#     conversation_ttl: int = 86400  # 24 hours
#     enable_caching: bool = True
    
#     class Config:
#         env_file = ".env"

# settings = Settings()

"""
Application settings using Pydantic BaseSettings.
Loads configuration from environment variables.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_version: str = "v1"
    app_name: str = "PersonX AI Assistant"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database (optional for simple mode)
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = ""
    database_url: str | None = None
    
    # Redis (optional for simple mode)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    
    # Gemini (simple mode)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    
    # Vector Database (Optional for Phase 1)
    pinecone_api_key: str = ""
    pinecone_environment: str = ""
    pinecone_index_name: str = ""
    
    # Security (optional for simple mode)
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # LLM Configuration
    default_max_tokens: int = 1024
    default_temperature: float = 0.7

    # Embeddings (Local / Free)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.2
    retrieval_chunk_size: int = 1000
    retrieval_chunk_overlap: int = 200
    
    # Monitoring
    langsmith_api_key: str = ""
    langsmith_project: str = "personx-ai"
    sentry_dsn: str = ""
    
    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str | None, info) -> str:
        """Construct database URL if not explicitly provided."""
        if v:
            return v
        values = info.data
        if not values.get("postgres_user") or not values.get("postgres_db"):
            return ""
        return (
            f"postgresql+asyncpg://{values.get('postgres_user')}:"
            f"{values.get('postgres_password')}@"
            f"{values.get('postgres_host')}:{values.get('postgres_port')}/"
            f"{values.get('postgres_db')}"
        )
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use this function throughout the application to access settings.
    """
    return Settings()
