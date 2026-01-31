"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import Mock

from backend.app.config import Settings
from backend.app.services.dicom_parser import DicomParserService
from backend.app.services.kheops_service import KheopsService
from backend.app.services.llm_service import LLMService
from backend.app.services.monai_service import MonaiService
from backend.app.services.report_generator import ReportGenerator


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        kheops_base_url="https://test.kheops.online",
        kheops_album_token="test_token",
        monai_model_path="test_model.pth",
        monai_device="cpu",
        llm_model_name="test_model",
        ollama_base_url="http://test:11434",
    )


@pytest.fixture
def mock_kheops_service():
    """Create mock Kheops service."""
    return Mock(spec=KheopsService)


@pytest.fixture
def mock_dicom_parser():
    """Create mock DICOM parser."""
    return Mock(spec=DicomParserService)


@pytest.fixture
def mock_monai_service():
    """Create mock MONAI service."""
    return Mock(spec=MonaiService)


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    return Mock(spec=LLMService)


@pytest.fixture
def mock_report_generator(mock_kheops_service, mock_dicom_parser, mock_monai_service, mock_llm_service):
    """Create mock report generator."""
    return Mock(spec=ReportGenerator)
