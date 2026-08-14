from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str
    APP_ENV: str
    DEBUG: bool
    LOG_LEVEL: str

    # Ollama
    OLLAMA_BASE_URL: str
    LLM_MODEL: str
    EMBEDDING_MODEL: str

    # Database
    DATABASE_URL: str

    # Vector Store
    VECTOR_STORE_PATH: str

    # Raw Documents
    RAW_DATA_PATH: str

    # Chunking
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int

    # Retrieval
    TOP_K: int
    FINAL_CONTEXT_K: int
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
    )


settings = Settings()