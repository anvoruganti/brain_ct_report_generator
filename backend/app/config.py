"""Configuration management using pydantic-settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Kheops Configuration
    kheops_base_url: str = Field(
        default="https://demo.kheops.online",
        description="Base URL for Kheops DICOMweb API",
    )
    kheops_album_token: str = Field(
        default="",
        description="Album token for Kheops authentication",
    )

    # MONAI Configuration
    monai_model_path: str = Field(
        default="models/brain_ct_model.pth",
        description="Path to MONAI model file",
    )
    monai_device: str = Field(
        default="cuda",
        description="Device for MONAI inference (cuda or cpu)",
    )

    # LLM Configuration
    llm_model_name: str = Field(
        default="llama3",
        description="Name of the LLM model to use",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API",
    )

    # FastAPI Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="Host for FastAPI server",
    )
    api_port: int = Field(
        default=8000,
        description="Port for FastAPI server",
    )
    api_reload: bool = Field(
        default=True,
        description="Enable auto-reload for development",
    )
    cors_origins: List[str] = Field(
        default=["http://localhost:8501"],
        description="Allowed CORS origins",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
