"""Unit tests for LLM service."""

from unittest.mock import Mock, patch

import httpx
import pytest

from backend.app.config import Settings
from backend.app.models.domain import ClinicalReport, DiagnosisResult
from backend.app.services.llm_service import LLMService
from backend.app.utils.exceptions import LLMInitializationError


class TestLLMService:
    """Test LLMService class."""

    def test_init_with_default_settings(self):
        """Test initialization with default settings."""
        # Arrange: No setup needed
        # Act: Create service instance
        service = LLMService()

        # Assert: Verify settings
        assert service.settings is not None
        assert service.model_name == "llama3"
        assert service.initialized is False

    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        # Arrange: Create custom settings
        custom_settings = Settings(llm_model_name="llama2", ollama_base_url="http://custom:11434")

        # Act: Create service with custom settings
        service = LLMService(settings=custom_settings)

        # Assert: Verify custom settings are used
        assert service.model_name == "llama2"
        assert service.base_url == "http://custom:11434"

    @patch("backend.app.services.llm_service.httpx.Client")
    def test_initialize_llm_success(self, mock_client_class):
        """Test successful LLM initialization."""
        # Arrange: Mock Ollama API response
        mock_response = Mock()
        mock_response.json.return_value = {"models": [{"name": "llama3:latest"}]}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = LLMService()

        # Act: Initialize LLM
        service.initialize_llm()

        # Assert: Verify initialization
        assert service.initialized is True

    @patch("backend.app.services.llm_service.httpx.Client")
    def test_initialize_llm_model_not_found(self, mock_client_class):
        """Test initialization with model not found."""
        # Arrange: Mock Ollama API response without model
        mock_response = Mock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = LLMService()

        # Act & Assert: Verify LLMInitializationError is raised
        with pytest.raises(LLMInitializationError):
            service.initialize_llm()

    def test_create_prompt_with_diagnosis(self):
        """Test prompt creation from diagnosis."""
        # Arrange: Create diagnosis result
        diagnosis = DiagnosisResult(
            abnormalities=["hemorrhage", "edema"],
            confidence_scores={"normal": 0.2, "abnormal": 0.8},
            findings={"max_probability": 0.85},
        )
        service = LLMService()

        # Act: Create prompt
        prompt = service.create_prompt(diagnosis)

        # Assert: Verify prompt content
        assert "hemorrhage" in prompt
        assert "edema" in prompt
        assert "Clinical History" in prompt
        assert "Findings" in prompt
        assert "Impression" in prompt
        assert "Recommendations" in prompt

    def test_create_prompt_no_abnormalities(self):
        """Test prompt creation with no abnormalities."""
        # Arrange: Create diagnosis with no abnormalities
        diagnosis = DiagnosisResult(
            abnormalities=[],
            confidence_scores={"normal": 0.9, "abnormal": 0.1},
            findings={},
        )
        service = LLMService()

        # Act: Create prompt
        prompt = service.create_prompt(diagnosis)

        # Assert: Verify prompt includes "None detected"
        assert "None detected" in prompt

    @patch("backend.app.services.llm_service.httpx.Client")
    def test_generate_report_success(self, mock_client_class):
        """Test successful report generation."""
        # Arrange: Mock Ollama generate API
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Test report content"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = LLMService()
        service.initialized = True
        prompt = "Test prompt"

        # Act: Generate report
        report = service.generate_report(prompt)

        # Assert: Verify report content
        assert report == "Test report content"

    def test_format_report_success(self):
        """Test report formatting."""
        # Arrange: Create raw report text
        raw_text = """Clinical History:
Patient presents with headache.

Findings:
CT scan shows normal brain structure.

Impression:
No acute abnormalities.

Recommendations:
Follow-up in 3 months."""

        service = LLMService()

        # Act: Format report
        report = service.format_report(raw_text)

        # Assert: Verify formatted report
        assert isinstance(report, ClinicalReport)
        assert "headache" in report.clinical_history
        assert "normal brain structure" in report.findings
        assert "No acute abnormalities" in report.impression
        assert "Follow-up" in report.recommendations

    def test_extract_section_not_found(self):
        """Test section extraction when section not found."""
        # Arrange: Text without section
        text = "Some random text without sections."
        service = LLMService()

        # Act: Extract section
        section = service._extract_section(text, "Findings")

        # Assert: Verify None returned
        assert section is None
