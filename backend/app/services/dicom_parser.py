"""DICOM file parsing service."""

from io import BytesIO
from typing import Dict, Any

import numpy as np
import pydicom

from backend.app.models.domain import DicomData
from backend.app.services.interfaces import IDicomParser
from backend.app.utils.exceptions import DicomParseError


class DicomParserService(IDicomParser):
    """Service for parsing DICOM files."""

    def parse_dicom_file(self, dicom_bytes: bytes) -> DicomData:
        """
        Parse DICOM file bytes into DicomData object.

        Args:
            dicom_bytes: Raw DICOM file bytes

        Returns:
            Parsed DicomData object

        Raises:
            DicomParseError: If parsing fails
        """
        try:
            # Check if content is JSON (metadata) instead of binary DICOM
            if dicom_bytes.startswith(b"{") or dicom_bytes.startswith(b"["):
                raise DicomParseError(
                    "Received JSON metadata instead of binary DICOM file. "
                    "The Kheops API may not support direct file downloads."
                )
            
            # Check for DICOM signature at offset 128 (only for files large enough)
            # Files created by pydicom.dcmwrite may not have this signature, so we're lenient
            if len(dicom_bytes) >= 132:
                has_dicm_signature = (
                    dicom_bytes[128:132] == b"DICM" or 
                    dicom_bytes[:4] == b"DICM"
                )
                # If file is large but doesn't have DICM signature, it might be invalid
                # But we'll still try to parse it in case it's a valid DICOM without header
                if len(dicom_bytes) > 10000 and not has_dicm_signature:
                    # For large files, require DICM signature to avoid parsing JSON/metadata
                    raise DicomParseError(
                        "File does not appear to be a valid DICOM file. "
                        "Missing DICM signature. "
                        "The downloaded content may be metadata instead of binary DICOM data."
                    )
            
            # Try reading DICOM file
            dicom_file = None
            parse_error = None
            
            try:
                dicom_file = pydicom.dcmread(BytesIO(dicom_bytes))
            except Exception as e:
                parse_error = e
                # If standard read fails, try with force=True
                try:
                    dicom_file = pydicom.dcmread(BytesIO(dicom_bytes), force=True)
                except Exception as force_error:
                    raise DicomParseError(
                        f"Failed to parse DICOM file: {str(e)}. "
                        f"Force parsing also failed: {str(force_error)}"
                    )
            
            # Verify we got a proper Dataset with required attributes
            if dicom_file is None:
                raise DicomParseError("Failed to read DICOM file")
            
            # Check if it's a FileMetaDataset (incomplete file)
            if hasattr(dicom_file, 'file_meta') and not hasattr(dicom_file, 'StudyInstanceUID'):
                raise DicomParseError(
                    "DICOM file appears to be incomplete or metadata-only. "
                    "Received FileMetaDataset instead of full Dataset."
                )
            
            metadata = self._extract_metadata(dicom_file)
            metadata["raw_bytes"] = dicom_bytes

            return DicomData(
                study_id=self._get_tag_value(dicom_file, "StudyInstanceUID"),
                series_id=self._get_tag_value(dicom_file, "SeriesInstanceUID"),
                instance_id=self._get_tag_value(dicom_file, "SOPInstanceUID"),
                patient_id=self._get_tag_value(dicom_file, "PatientID"),
                patient_name=self._get_tag_value(dicom_file, "PatientName"),
                study_date=self._get_tag_value(dicom_file, "StudyDate"),
                metadata=metadata,
            )
        except Exception as e:
            raise DicomParseError(f"Failed to parse DICOM file: {str(e)}") from e

    def extract_pixel_array(self, dicom_data: DicomData) -> np.ndarray:
        """
        Extract pixel array from DICOM data.

        Args:
            dicom_data: Parsed DICOM data

        Returns:
            NumPy array of pixel data

        Raises:
            DicomParseError: If extraction fails
        """
        try:
            dicom_bytes = dicom_data.metadata.get("raw_bytes")
            if dicom_bytes is None:
                raise DicomParseError("Raw DICOM bytes not found in metadata")

            # Try reading DICOM file
            dicom_file = None
            try:
                dicom_file = pydicom.dcmread(BytesIO(dicom_bytes))
            except Exception:
                # If standard read fails, try with force=True
                try:
                    dicom_file = pydicom.dcmread(BytesIO(dicom_bytes), force=True)
                except Exception as e:
                    raise DicomParseError(f"Failed to read DICOM file: {str(e)}")
            
            if dicom_file is None:
                raise DicomParseError("Failed to read DICOM file")
            
            # Verify pixel data is available
            if not hasattr(dicom_file, 'pixel_array'):
                raise DicomParseError(
                    "DICOM file does not contain pixel data. "
                    "This may be a metadata-only file."
                )
            
            try:
                pixel_array = dicom_file.pixel_array
            except AttributeError as e:
                raise DicomParseError(
                    f"Failed to extract pixel array: {str(e)}. "
                    "The DICOM file may be incomplete or corrupted."
                )

            return pixel_array.astype(np.float32)
        except Exception as e:
            raise DicomParseError(f"Failed to extract pixel array: {str(e)}") from e

    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize image array for model input.

        Args:
            image: Image array

        Returns:
            Normalized image array
        """
        if image.size == 0:
            return image

        min_val = np.min(image)
        max_val = np.max(image)

        if max_val == min_val:
            return np.zeros_like(image)

        normalized = (image - min_val) / (max_val - min_val)
        return normalized.astype(np.float32)

    def _get_tag_value(self, dicom_file: pydicom.Dataset, tag_name: str) -> str | None:
        """
        Get DICOM tag value safely.

        Args:
            dicom_file: Pydicom dataset
            tag_name: Name of the DICOM tag

        Returns:
            Tag value as string or None if not found
        """
        try:
            tag_value = getattr(dicom_file, tag_name, None)
            if tag_value is None:
                return None

            if isinstance(tag_value, pydicom.multival.MultiValue):
                return str(tag_value[0]) if len(tag_value) > 0 else None

            return str(tag_value)
        except Exception:
            return None

    def _extract_metadata(self, dicom_file: pydicom.Dataset) -> Dict[str, Any]:
        """
        Extract metadata from DICOM file.

        Args:
            dicom_file: Pydicom dataset

        Returns:
            Dictionary with metadata
        """
        metadata = {
            "modality": getattr(dicom_file, "Modality", None),
            "slice_thickness": getattr(dicom_file, "SliceThickness", None),
            "pixel_spacing": getattr(dicom_file, "PixelSpacing", None),
            "rows": getattr(dicom_file, "Rows", None),
            "columns": getattr(dicom_file, "Columns", None),
        }

        return metadata
