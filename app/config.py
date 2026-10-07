from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    anthropic_api_key: str = ""
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50
    ingest_api_key: str = "change-me"
    allowed_origins: str = "http://localhost:5173"


settings = Settings()
