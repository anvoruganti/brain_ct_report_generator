"""Unit tests for report generator service."""

from unittest.mock import Mock

import pytest

from backend.app.models.domain import ClinicalReport, DiagnosisResult, DicomData, Series
from backend.app.services.dicom_parser import DicomParserService
from backend.app.services.kheops_service import KheopsService
from backend.app.services.llm_service import LLMService
from backend.app.services.monai_service import MonaiService
from backend.app.services.report_generator import ReportGenerator
from backend.app.utils.exceptions import ReportGenerationError


class TestReportGenerator:
    """Test ReportGenerator class."""

    def test_init_with_default_dependencies(self):
        """Test initialization with default dependencies."""
        # Arrange: No setup needed
        # Act: Create generator instance
        generator = ReportGenerator()

        # Assert: Verify dependencies are initialized
        assert isinstance(generator.kheops_client, KheopsService)
        assert isinstance(generator.dicom_parser, DicomParserService)
        assert isinstance(generator.diagnosis_provider, MonaiService)
        assert isinstance(generator.report_generator, LLMService)

    def test_init_with_custom_dependencies(self):
        """Test initialization with custom dependencies."""
        # Arrange: Create mock dependencies
        mock_kheops = Mock(spec=KheopsService)
        mock_parser = Mock(spec=DicomParserService)
        mock_monai = Mock(spec=MonaiService)
        mock_llm = Mock(spec=LLMService)

        # Act: Create generator with custom dependencies
        generator = ReportGenerator(
            kheops_client=mock_kheops,
            dicom_parser=mock_parser,
            diagnosis_provider=mock_monai,
            report_generator=mock_llm,
        )

        # Assert: Verify custom dependencies are used
        assert generator.kheops_client == mock_kheops
        assert generator.dicom_parser == mock_parser
        assert generator.diagnosis_provider == mock_monai
        assert generator.report_generator == mock_llm

    def test_generate_report_from_dicom_success(self):
        """Test successful report generation from DICOM bytes."""
        # Arrange: Create mocks
        mock_parser = Mock(spec=DicomParserService)
        mock_monai = Mock(spec=MonaiService)
        mock_llm = Mock(spec=LLMService)

        dicom_data = DicomData(study_id="study1", patient_id="patient1")
        pixel_array = Mock()
        normalized_image = Mock()
        image_tensor = Mock()
        diagnosis = DiagnosisResult(abnormalities=["abnormal"], confidence_scores={"normal": 0.3, "abnormal": 0.7}, findings={})
        prompt = "Test prompt"
        raw_report = "Test report"
        clinical_report = ClinicalReport(findings="Test findings")

        mock_parser.parse_dicom_file.return_value = dicom_data
        mock_parser.extract_pixel_array.return_value = pixel_array
        mock_parser.normalize_image.return_value = normalized_image
        mock_monai.preprocess_image.return_value = image_tensor
        mock_monai.run_inference.return_value = diagnosis
        mock_llm.create_prompt.return_value = prompt
        mock_llm.generate_report.return_value = raw_report
        mock_llm.format_report.return_value = clinical_report

        generator = ReportGenerator(
            dicom_parser=mock_parser,
            diagnosis_provider=mock_monai,
            report_generator=mock_llm,
        )

        dicom_bytes = b"test_dicom_bytes"

        # Act: Generate report
        result = generator.generate_report_from_dicom(dicom_bytes)

        # Assert: Verify result structure
        assert "report" in result
        assert "diagnosis" in result
        assert "dicom_metadata" in result
        assert result["report"] == clinical_report
        assert result["diagnosis"] == diagnosis

    def test_generate_report_from_album_success(self):
        """Test successful report generation from album."""
        # Arrange: Create mocks
        mock_kheops = Mock(spec=KheopsService)
        mock_parser = Mock(spec=DicomParserService)
        mock_monai = Mock(spec=MonaiService)
        mock_llm = Mock(spec=LLMService)

        series = Series(series_id="series1", study_id="study1")
        mock_kheops.fetch_series.return_value = [series]
        mock_kheops.fetch_instances.return_value = ["instance1"]
        mock_kheops.download_instance.return_value = b"dicom_bytes"

        dicom_data = DicomData(study_id="study1")
        pixel_array = Mock()
        normalized_image = Mock()
        image_tensor = Mock()
        diagnosis = DiagnosisResult(abnormalities=[], confidence_scores={"normal": 0.9}, findings={})
        prompt = "Test prompt"
        raw_report = "Test report"
        clinical_report = ClinicalReport()

        mock_parser.parse_dicom_file.return_value = dicom_data
        mock_parser.extract_pixel_array.return_value = pixel_array
        mock_parser.normalize_image.return_value = normalized_image
        mock_monai.preprocess_image.return_value = image_tensor
        mock_monai.run_inference.return_value = diagnosis
        mock_llm.create_prompt.return_value = prompt
        mock_llm.generate_report.return_value = raw_report
        mock_llm.format_report.return_value = clinical_report

        generator = ReportGenerator(
            kheops_client=mock_kheops,
            dicom_parser=mock_parser,
            diagnosis_provider=mock_monai,
            report_generator=mock_llm,
        )

        # Act: Generate report
        result = generator.generate_report_from_album("token", "study1")

        # Assert: Verify result
        assert "report" in result
        mock_kheops.fetch_series.assert_called_once()
        mock_kheops.fetch_instances.assert_called_once_with("token", "study1", "series1")
        mock_kheops.download_instance.assert_called_once_with("token", "study1", "series1", "instance1")

    def test_generate_report_from_album_no_series(self):
        """Test report generation with no series found."""
        # Arrange: Mock empty series list
        mock_kheops = Mock(spec=KheopsService)
        mock_kheops.fetch_series.return_value = []

        generator = ReportGenerator(kheops_client=mock_kheops)

        # Act & Assert: Verify ReportGenerationError is raised
        with pytest.raises(ReportGenerationError):
            generator.generate_report_from_album("token", "study1")

    def test_generate_report_from_album_no_instances(self):
        """Test report generation with no instances found."""
        # Arrange: Mock series with no instances
        mock_kheops = Mock(spec=KheopsService)
        series = Series(series_id="series1", study_id="study1")
        mock_kheops.fetch_series.return_value = [series]
        mock_kheops.fetch_instances.return_value = []

        generator = ReportGenerator(kheops_client=mock_kheops)

        # Act & Assert: Verify ReportGenerationError is raised
        with pytest.raises(ReportGenerationError):
            generator.generate_report_from_album("token", "study1")

    def test_generate_report_from_dicom_error(self):
        """Test report generation with DICOM parsing error."""
        # Arrange: Mock parser error
        mock_parser = Mock(spec=DicomParserService)
        mock_parser.parse_dicom_file.side_effect = Exception("Parse error")

        generator = ReportGenerator(dicom_parser=mock_parser)

        # Act & Assert: Verify ReportGenerationError is raised
        with pytest.raises(ReportGenerationError):
            generator.generate_report_from_dicom(b"invalid_bytes")
