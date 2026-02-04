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

    # Kheops Configuration (Optional - Disabled for PoC)
    enable_kheops: bool = Field(
        default=False,
        description="Enable Kheops integration (disabled for PoC, will be replaced with AWS HealthImaging for MVP)",
    )
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
        default="auto",
        description="Device for MONAI inference (auto, mps, cuda, or cpu). 'auto' detects best available.",
    )
    monai_batch_size: int = Field(
        default=16,
        description="Batch size for MONAI inference (8-32 recommended for M1 Mac, higher for CUDA)",
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
    llm_timeout: int = Field(
        default=60,
        description="Timeout in seconds for LLM requests",
    )
    
    # Parallel Processing Configuration
    chunk_size: int = Field(
        default=10,
        description="Number of DICOM files to process per chunk",
    )
    max_workers: int = Field(
        default=4,
        description="Maximum number of parallel workers for processing",
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
    max_upload_size_mb: int = Field(
        default=500,
        description="Maximum file upload size in MB (for ZIP files and DICOM series)",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
