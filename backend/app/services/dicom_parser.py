"""DICOM file parsing service."""

import logging
import traceback
from io import BytesIO
from typing import Dict, Any

import numpy as np
import pydicom

from backend.app.models.domain import DicomData
from backend.app.services.interfaces import IDicomParser
from backend.app.utils.exceptions import DicomParseError

logger = logging.getLogger(__name__)


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
        
        Handles compressed pixel data (JPEG, JPEG-LS, JPEG2000) using pylibjpeg
        or gdcm if available. Provides detailed error messages if pixel decoding fails.

        Args:
            dicom_data: Parsed DICOM data

        Returns:
            NumPy array of pixel data

        Raises:
            DicomParseError: If extraction fails, with detailed error message
        """
        try:
            dicom_bytes = dicom_data.metadata.get("raw_bytes")
            if dicom_bytes is None:
                raise DicomParseError("Raw DICOM bytes not found in metadata")

            # Try reading DICOM file
            dicom_file = None
            try:
                dicom_file = pydicom.dcmread(BytesIO(dicom_bytes))
            except Exception as e:
                # If standard read fails, try with force=True
                try:
                    dicom_file = pydicom.dcmread(BytesIO(dicom_bytes), force=True)
                except Exception as force_error:
                    logger.error(f"DICOM read failed: {str(e)}. Force read also failed: {str(force_error)}")
                    logger.debug(traceback.format_exc())
                    raise DicomParseError(
                        f"Failed to read DICOM file: {str(e)}. "
                        f"Force parsing also failed: {str(force_error)}"
                    )
            
            if dicom_file is None:
                raise DicomParseError("Failed to read DICOM file")
            
            # Check for pixel data
            if not hasattr(dicom_file, 'PixelData') and not hasattr(dicom_file, 'pixel_array'):
                raise DicomParseError(
                    "DICOM file does not contain pixel data. "
                    "This may be a metadata-only file."
                )
            
            # Get transfer syntax to diagnose compression issues
            transfer_syntax = getattr(dicom_file, 'file_meta', {}).get('TransferSyntaxUID', 'Unknown') if hasattr(dicom_file, 'file_meta') else 'Unknown'
            
            # Try to extract pixel array
            try:
                pixel_array = dicom_file.pixel_array
            except Exception as pixel_error:
                # Provide detailed error message based on transfer syntax
                error_msg = f"Failed to extract pixel array: {str(pixel_error)}"
                
                # Check if it's a compression issue
                if 'compressed' in str(pixel_error).lower() or 'jpeg' in str(pixel_error).lower() or 'decompress' in str(pixel_error).lower():
                    error_msg += (
                        f"\n\n⚠️ PIXEL DECODING ERROR - Compressed DICOM detected!\n"
                        f"Transfer Syntax: {transfer_syntax}\n"
                        f"This DICOM uses compressed pixel data (JPEG/JPEG-LS/JPEG2000).\n"
                        f"Install pixel decoding libraries:\n"
                        f"  pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg\n"
                        f"OR:\n"
                        f"  pip install gdcm\n"
                        f"\nCurrent error: {type(pixel_error).__name__}: {str(pixel_error)}"
                    )
                    logger.error(error_msg)
                    logger.debug(traceback.format_exc())
                else:
                    logger.error(f"Pixel extraction error: {str(pixel_error)}")
                    logger.debug(traceback.format_exc())
                
                raise DicomParseError(error_msg) from pixel_error

            if pixel_array is None or pixel_array.size == 0:
                raise DicomParseError(
                    "Extracted pixel array is empty. "
                    "The DICOM file may be corrupted or incomplete."
                )

            return pixel_array.astype(np.float32)
        except DicomParseError:
            # Re-raise DicomParseError as-is (already has good error message)
            raise
        except Exception as e:
            # Catch any other exceptions and provide full traceback
            logger.error(f"Unexpected error extracting pixel array: {str(e)}")
            logger.debug(traceback.format_exc())
            raise DicomParseError(
                f"Failed to extract pixel array: {str(e)}. "
                f"See logs for full traceback."
            ) from e

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
