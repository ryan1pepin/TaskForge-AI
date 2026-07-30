import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Database Settings
    # Use postgresql+asyncpg for SQLAlchemy async operations
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/taskforge",
        validation_alias="DATABASE_URL"
    )

    # Security Settings
    JWT_SECRET_KEY: str = Field(
        default="e2b0c15d48af3102c019918a994ef9281a6296b4ef84c98c1a3b1a2936de398d", # Example secure key
        validation_alias="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=5)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # CORS Settings
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:5173"])

    # AI / LLM Settings — local Ollama by default, falls back to cloud OpenAI if BASE_URL empty
    OPENAI_API_KEY: str = Field(default="ollama")  # Ollama doesn't require a real key
    OPENAI_MODEL: str = Field(default="gemma2:2b")  # lightweight model, doesn't conflict with qwen-hermes
    OPENAI_BASE_URL: str = Field(default="http://localhost:11434/v1")

    # Load configuration from .env file if it exists
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
