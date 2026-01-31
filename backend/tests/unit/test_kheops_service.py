"""Unit tests for Kheops service."""

from unittest.mock import Mock, patch

import pytest
import requests

from backend.app.config import Settings
from backend.app.models.domain import Series, Study
from backend.app.services.kheops_service import KheopsService
from backend.app.utils.exceptions import KheopsAPIError


class TestKheopsService:
    """Test KheopsService class."""

    def test_init_with_default_settings(self):
        """Test initialization with default settings."""
        # Arrange: No setup needed
        # Act: Create service instance
        service = KheopsService()

        # Assert: Verify settings are loaded
        assert service.settings is not None
        assert service.base_url == "https://demo.kheops.online"

    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        # Arrange: Create custom settings
        custom_settings = Settings(kheops_base_url="https://custom.kheops.online")

        # Act: Create service with custom settings
        service = KheopsService(settings=custom_settings)

        # Assert: Verify custom settings are used
        assert service.settings == custom_settings
        assert service.base_url == "https://custom.kheops.online"

    def test_get_headers_includes_authorization(self):
        """Test that headers include authorization token."""
        # Arrange: Create service and token
        service = KheopsService()
        token = "test_token_123"

        # Act: Get headers
        headers = service._get_headers(token)

        # Assert: Verify authorization header
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {token}"

    @patch("backend.app.services.kheops_service.requests.request")
    def test_fetch_studies_success(self, mock_request):
        """Test successful fetch_studies call."""
        # Arrange: Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "0020000D": {"Value": ["study1"]},
                "00080020": {"Value": ["20240101"]},
                "00081030": {"Value": ["Brain CT"]},
                "00100020": {"Value": ["patient1"]},
                "00100010": {"Value": ["John^Doe"]},
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        service = KheopsService()
        token = "test_token"

        # Act: Fetch studies
        studies = service.fetch_studies(token)

        # Assert: Verify studies are parsed correctly
        assert len(studies) == 1
        assert isinstance(studies[0], Study)
        assert studies[0].study_id == "study1"
        assert studies[0].study_date == "20240101"
        assert studies[0].study_description == "Brain CT"

    @patch("backend.app.services.kheops_service.requests.request")
    def test_fetch_studies_api_error(self, mock_request):
        """Test fetch_studies with API error."""
        # Arrange: Mock API error
        mock_request.side_effect = requests.exceptions.RequestException("API Error")

        service = KheopsService()
        token = "test_token"

        # Act & Assert: Verify KheopsAPIError is raised
        with pytest.raises(KheopsAPIError):
            service.fetch_studies(token)

    @patch("backend.app.services.kheops_service.requests.request")
    def test_fetch_series_success(self, mock_request):
        """Test successful fetch_series call."""
        # Arrange: Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "0020000E": {"Value": ["series1"]},
                "0008103E": {"Value": ["Axial"]},
                "00080060": {"Value": ["CT"]},
                "00081190": {"Value": ["instance1", "instance2"]},
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        service = KheopsService()
        token = "test_token"
        study_id = "study1"

        # Act: Fetch series
        series_list = service.fetch_series(token, study_id)

        # Assert: Verify series are parsed correctly
        assert len(series_list) == 1
        assert isinstance(series_list[0], Series)
        assert series_list[0].series_id == "series1"
        assert series_list[0].study_id == study_id
        assert series_list[0].modality == "CT"

    @patch("backend.app.services.kheops_service.requests.get")
    def test_download_instance_success(self, mock_get):
        """Test successful download_instance call."""
        # Arrange: Mock successful download
        mock_response = Mock()
        mock_response.content = b"DICOM_FILE_CONTENT"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        service = KheopsService()
        token = "test_token"
        instance_id = "instance1"

        # Act: Download instance
        content = service.download_instance(token, instance_id)

        # Assert: Verify content is returned
        assert content == b"DICOM_FILE_CONTENT"
        mock_get.assert_called_once()

    @patch("backend.app.services.kheops_service.requests.get")
    def test_download_instance_error(self, mock_get):
        """Test download_instance with error."""
        # Arrange: Mock download error
        mock_get.side_effect = requests.exceptions.RequestException("Download Error")

        service = KheopsService()
        token = "test_token"
        instance_id = "instance1"

        # Act & Assert: Verify KheopsAPIError is raised
        with pytest.raises(KheopsAPIError):
            service.download_instance(token, instance_id)
