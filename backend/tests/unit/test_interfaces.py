"""Unit tests for interfaces module."""

import pytest

from backend.app.models.domain import DiagnosisResult, DicomData, Series, Study
from backend.app.services.interfaces import (
    IDicomParser,
    IDiagnosisProvider,
    IKheopsClient,
    IReportGenerator,
)


class TestKheopsClient:
    """Test IKheopsClient interface."""

    def test_interface_cannot_be_instantiated(self):
        """Test that interface cannot be instantiated directly."""
        # Arrange: No setup needed
        # Act & Assert: Verify TypeError is raised
        with pytest.raises(TypeError):
            IKheopsClient()  # type: ignore

    def test_interface_has_required_methods(self):
        """Test that interface defines required methods."""
        # Arrange: Check interface methods
        # Act: Inspect interface
        methods = [method for method in dir(IKheopsClient) if not method.startswith("_")]

        # Assert: Verify required methods exist
        assert "fetch_studies" in methods
        assert "fetch_series" in methods
        assert "download_instance" in methods


class TestDicomParser:
    """Test IDicomParser interface."""

    def test_interface_cannot_be_instantiated(self):
        """Test that interface cannot be instantiated directly."""
        # Arrange: No setup needed
        # Act & Assert: Verify TypeError is raised
        with pytest.raises(TypeError):
            IDicomParser()  # type: ignore

    def test_interface_has_required_methods(self):
        """Test that interface defines required methods."""
        # Arrange: Check interface methods
        # Act: Inspect interface
        methods = [method for method in dir(IDicomParser) if not method.startswith("_")]

        # Assert: Verify required methods exist
        assert "parse_dicom_file" in methods
        assert "extract_pixel_array" in methods
        assert "normalize_image" in methods


class TestDiagnosisProvider:
    """Test IDiagnosisProvider interface."""

    def test_interface_cannot_be_instantiated(self):
        """Test that interface cannot be instantiated directly."""
        # Arrange: No setup needed
        # Act & Assert: Verify TypeError is raised
        with pytest.raises(TypeError):
            IDiagnosisProvider()  # type: ignore

    def test_interface_has_required_methods(self):
        """Test that interface defines required methods."""
        # Arrange: Check interface methods
        # Act: Inspect interface
        methods = [method for method in dir(IDiagnosisProvider) if not method.startswith("_")]

        # Assert: Verify required methods exist
        assert "load_model" in methods
        assert "preprocess_image" in methods
        assert "run_inference" in methods


class TestReportGenerator:
    """Test IReportGenerator interface."""

    def test_interface_cannot_be_instantiated(self):
        """Test that interface cannot be instantiated directly."""
        # Arrange: No setup needed
        # Act & Assert: Verify TypeError is raised
        with pytest.raises(TypeError):
            IReportGenerator()  # type: ignore

    def test_interface_has_required_methods(self):
        """Test that interface defines required methods."""
        # Arrange: Check interface methods
        # Act: Inspect interface
        methods = [method for method in dir(IReportGenerator) if not method.startswith("_")]

        # Assert: Verify required methods exist
        assert "initialize_llm" in methods
        assert "create_prompt" in methods
        assert "generate_report" in methods
        assert "format_report" in methods
