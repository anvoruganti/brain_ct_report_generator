"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from backend.app.config import Settings, get_settings


def test_settings_loads_default_values():
    """Test that Settings loads default values correctly."""
    # Arrange: No environment variables set
    # Act: Create settings instance
    settings = Settings()

    # Assert: Verify default values
    assert settings.kheops_base_url == "https://demo.kheops.online"
    assert settings.monai_device == "cuda"
    assert settings.llm_model_name == "llama3"
    assert settings.api_port == 8000
    assert settings.log_level == "INFO"


def test_settings_loads_from_environment():
    """Test that Settings loads values from environment variables."""
    # Arrange: Set environment variables
    env_vars = {
        "KHEOPS_BASE_URL": "https://custom.kheops.online",
        "KHEOPS_ALBUM_TOKEN": "test_token_123",
        "MONAI_DEVICE": "cpu",
        "LLM_MODEL_NAME": "llama2",
        "API_PORT": "9000",
    }

    # Act: Create settings with environment variables
    with patch.dict(os.environ, env_vars):
        settings = Settings()

    # Assert: Verify environment values are loaded
    assert settings.kheops_base_url == "https://custom.kheops.online"
    assert settings.kheops_album_token == "test_token_123"
    assert settings.monai_device == "cpu"
    assert settings.llm_model_name == "llama2"
    assert settings.api_port == 9000


def test_settings_cors_origins_default():
    """Test that CORS origins defaults to localhost."""
    # Arrange: No CORS_ORIGINS set
    # Act: Create settings instance
    settings = Settings()

    # Assert: Verify default CORS origins
    assert settings.cors_origins == ["http://localhost:8501"]
    assert isinstance(settings.cors_origins, list)


def test_get_settings_returns_settings_instance():
    """Test that get_settings returns a Settings instance."""
    # Arrange: No setup needed
    # Act: Call get_settings
    settings = get_settings()

    # Assert: Verify it returns Settings instance
    assert isinstance(settings, Settings)


def test_settings_api_reload_default():
    """Test that API reload defaults to True."""
    # Arrange: No API_RELOAD set
    # Act: Create settings instance
    settings = Settings()

    # Assert: Verify default reload value
    assert settings.api_reload is True
