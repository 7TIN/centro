from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Configuration
    anthropic_api_key: str
    openai_api_key: str
    primary_model: str = "claude-sonnet-4-20250514"
    fallback_model: str = "gpt-4"
    
    # Vector DB
    pinecone_api_key: str
    pinecone_index: str = "personx-knowledge"
    embedding_model: str = "text-embedding-3-small"
    
    # Database
    database_url: str
    redis_url: str
    
    # App Settings
    max_context_tokens: int = 8000
    conversation_ttl: int = 86400  # 24 hours
    enable_caching: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()