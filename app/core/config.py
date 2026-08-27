from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, validated environment configuration."""

    # Application
    APP_NAME: str = Field(default="FinDoc-RAG")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    # Ollama Local Service
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    LLM_MODEL: str = Field(default="llama3.2:3b")
    EMBEDDING_MODEL: str = Field(default="nomic-embed-text")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/findoc_rag"
    )

    # Security & CORS
    CORS_ORIGINS: list[str] | str = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]
    )

    # Rate Limiting
    RATE_LIMITING_ENABLED: bool = Field(default=True)
    RATE_LIMIT_CHAT: str = Field(default="30/minute")
    RATE_LIMIT_UPLOAD: str = Field(default="10/minute")
    RATE_LIMIT_DELETE: str = Field(default="10/minute")

    # Vector Store & Data Paths
    VECTOR_STORE_PATH: str = Field(default="./data/vector_store")
    RAW_DATA_PATH: str = Field(default="./data/raw")
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, gt=0)

    # Document Chunking Settings
    CHUNK_SIZE: int = Field(default=1000, gt=0)
    CHUNK_OVERLAP: int = Field(default=200, ge=0)

    # Retrieval & Reranking Settings
    TOP_K: int = Field(default=10, gt=0)
    FINAL_CONTEXT_K: int = Field(default=3, gt=0)
    RERANKER_MODEL: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v) -> list[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


    @field_validator("CHUNK_OVERLAP")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        chunk_size = info.data.get("CHUNK_SIZE", 1000)
        if v >= chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({v}) must be strictly less than CHUNK_SIZE ({chunk_size})"
            )
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid LOG_LEVEL '{v}'. Must be one of {valid_levels}")
        return v.upper()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()