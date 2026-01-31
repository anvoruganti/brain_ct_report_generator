"""Integration tests for API routes."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.domain import ClinicalReport, DiagnosisResult, Series, Study
from backend.app.models.schemas import ReportResponse


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_success(self):
        """Test successful health check."""
        # Arrange: Create test client
        client = TestClient(app)

        # Act: Call health endpoint
        response = client.get("/api/health")

        # Assert: Verify response
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestKheopsEndpoints:
    """Test Kheops-related endpoints."""

    @patch("backend.app.api.routes.get_kheops_service")
    def test_get_studies_success(self, mock_get_service):
        """Test successful get studies."""
        # Arrange: Mock service
        mock_service = Mock()
        mock_study = Study(study_id="study1", study_date="20240101")
        mock_service.fetch_studies.return_value = [mock_study]
        mock_get_service.return_value = mock_service

        client = TestClient(app)

        # Act: Call endpoint
        response = client.get("/api/kheops/studies?album_token=test_token")

        # Assert: Verify response
        assert response.status_code == 200
        assert len(response.json()["studies"]) == 1
        assert response.json()["studies"][0]["study_id"] == "study1"

    @patch("backend.app.api.routes.get_kheops_service")
    def test_get_series_success(self, mock_get_service):
        """Test successful get series."""
        # Arrange: Mock service
        mock_service = Mock()
        mock_series = Series(series_id="series1", study_id="study1")
        mock_service.fetch_series.return_value = [mock_series]
        mock_get_service.return_value = mock_service

        client = TestClient(app)

        # Act: Call endpoint
        response = client.get("/api/kheops/studies/study1/series?album_token=test_token")

        # Assert: Verify response
        assert response.status_code == 200
        assert len(response.json()["series"]) == 1
        assert response.json()["series"][0]["series_id"] == "series1"


class TestInferenceEndpoints:
    """Test inference endpoints."""

    @patch("backend.app.api.routes.get_report_generator")
    def test_generate_report_from_kheops_success(self, mock_get_generator):
        """Test successful report generation from Kheops."""
        # Arrange: Mock generator
        mock_generator = Mock()
        mock_report = ClinicalReport(findings="Test findings")
        mock_diagnosis = DiagnosisResult(abnormalities=[], confidence_scores={"normal": 0.9}, findings={})
        mock_generator.generate_report_from_album.return_value = {
            "report": mock_report,
            "diagnosis": mock_diagnosis,
            "dicom_metadata": {"study_id": "study1"},
        }
        mock_get_generator.return_value = mock_generator

        client = TestClient(app)

        # Act: Call endpoint
        response = client.post(
            "/api/inference/from-kheops",
            json={"album_token": "test_token", "study_id": "study1"},
        )

        # Assert: Verify response
        assert response.status_code == 200
        assert "report" in response.json()
        assert "diagnosis" in response.json()

    @patch("backend.app.api.routes.get_report_generator")
    def test_generate_report_from_dicom_success(self, mock_get_generator):
        """Test successful report generation from DICOM."""
        # Arrange: Mock generator
        mock_generator = Mock()
        mock_report = ClinicalReport(findings="Test findings")
        mock_diagnosis = DiagnosisResult(abnormalities=[], confidence_scores={"normal": 0.9}, findings={})
        mock_generator.generate_report_from_dicom.return_value = {
            "report": mock_report,
            "diagnosis": mock_diagnosis,
            "dicom_metadata": {"study_id": "study1"},
        }
        mock_get_generator.return_value = mock_generator

        client = TestClient(app)

        # Act: Call endpoint
        response = client.post(
            "/api/inference/from-dicom",
            files={"dicom_file": ("test.dcm", b"test_dicom_content", "application/dicom")},
        )

        # Assert: Verify response
        assert response.status_code == 200
        assert "report" in response.json()
        assert "diagnosis" in response.json()
