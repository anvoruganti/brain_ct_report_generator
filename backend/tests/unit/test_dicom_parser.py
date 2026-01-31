"""Unit tests for DICOM parser service."""

from io import BytesIO

import numpy as np
import pydicom
import pytest

from backend.app.models.domain import DicomData
from backend.app.services.dicom_parser import DicomParserService
from backend.app.utils.exceptions import DicomParseError


class TestDicomParserService:
    """Test DicomParserService class."""

    def test_parse_dicom_file_success(self):
        """Test successful DICOM file parsing."""
        # Arrange: Create mock DICOM file
        dicom_file = pydicom.Dataset()
        dicom_file.StudyInstanceUID = "1.2.3.4.5"
        dicom_file.SeriesInstanceUID = "1.2.3.4.5.6"
        dicom_file.SOPInstanceUID = "1.2.3.4.5.6.7"
        dicom_file.PatientID = "PATIENT001"
        dicom_file.PatientName = "Test^Patient"
        dicom_file.StudyDate = "20240101"
        dicom_file.Modality = "CT"
        dicom_file.Rows = 512
        dicom_file.Columns = 512

        buffer = BytesIO()
        pydicom.dcmwrite(buffer, dicom_file)
        dicom_bytes = buffer.getvalue()

        parser = DicomParserService()

        # Act: Parse DICOM file
        dicom_data = parser.parse_dicom_file(dicom_bytes)

        # Assert: Verify parsing results
        assert isinstance(dicom_data, DicomData)
        assert dicom_data.study_id == "1.2.3.4.5"
        assert dicom_data.series_id == "1.2.3.4.5.6"
        assert dicom_data.patient_id == "PATIENT001"
        assert dicom_data.metadata["modality"] == "CT"

    def test_parse_dicom_file_invalid_bytes(self):
        """Test parsing with invalid DICOM bytes."""
        # Arrange: Invalid bytes
        invalid_bytes = b"NOT_A_DICOM_FILE"
        parser = DicomParserService()

        # Act & Assert: Verify DicomParseError is raised
        with pytest.raises(DicomParseError):
            parser.parse_dicom_file(invalid_bytes)

    def test_extract_pixel_array_success(self):
        """Test successful pixel array extraction."""
        # Arrange: Create DICOM with pixel data
        dicom_file = pydicom.Dataset()
        dicom_file.StudyInstanceUID = "1.2.3.4.5"
        dicom_file.PixelData = np.random.randint(0, 255, (256, 256), dtype=np.uint16).tobytes()
        dicom_file.Rows = 256
        dicom_file.Columns = 256
        dicom_file.BitsAllocated = 16
        dicom_file.BitsStored = 16
        dicom_file.HighBit = 15
        dicom_file.PixelRepresentation = 0

        buffer = BytesIO()
        pydicom.dcmwrite(buffer, dicom_file)
        dicom_bytes = buffer.getvalue()

        dicom_data = DicomData(metadata={"raw_bytes": dicom_bytes})
        parser = DicomParserService()

        # Act: Extract pixel array
        pixel_array = parser.extract_pixel_array(dicom_data)

        # Assert: Verify pixel array
        assert isinstance(pixel_array, np.ndarray)
        assert pixel_array.dtype == np.float32
        assert pixel_array.shape == (256, 256)

    def test_extract_pixel_array_no_raw_bytes(self):
        """Test extraction when raw bytes are missing."""
        # Arrange: DicomData without raw_bytes
        dicom_data = DicomData(metadata={})
        parser = DicomParserService()

        # Act & Assert: Verify DicomParseError is raised
        with pytest.raises(DicomParseError):
            parser.extract_pixel_array(dicom_data)

    def test_normalize_image_success(self):
        """Test successful image normalization."""
        # Arrange: Create test image
        image = np.array([[0, 50, 100, 150, 200]], dtype=np.float32)
        parser = DicomParserService()

        # Act: Normalize image
        normalized = parser.normalize_image(image)

        # Assert: Verify normalization
        assert isinstance(normalized, np.ndarray)
        assert normalized.dtype == np.float32
        assert np.min(normalized) >= 0.0
        assert np.max(normalized) <= 1.0

    def test_normalize_image_empty(self):
        """Test normalization with empty image."""
        # Arrange: Empty image
        image = np.array([], dtype=np.float32)
        parser = DicomParserService()

        # Act: Normalize image
        normalized = parser.normalize_image(image)

        # Assert: Verify empty array returned
        assert isinstance(normalized, np.ndarray)
        assert normalized.size == 0

    def test_normalize_image_constant(self):
        """Test normalization with constant image."""
        # Arrange: Constant value image
        image = np.ones((10, 10), dtype=np.float32) * 100.0
        parser = DicomParserService()

        # Act: Normalize image
        normalized = parser.normalize_image(image)

        # Assert: Verify all zeros (since min == max)
        assert np.all(normalized == 0.0)
