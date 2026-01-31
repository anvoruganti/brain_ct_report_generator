"""Report generator service that orchestrates the end-to-end workflow."""

from typing import Dict, Any

from backend.app.models.domain import ClinicalReport, DiagnosisResult
from backend.app.services.dicom_parser import DicomParserService
from backend.app.services.interfaces import IDiagnosisProvider, IKheopsClient, IReportGenerator
from backend.app.services.kheops_service import KheopsService
from backend.app.services.llm_service import LLMService
from backend.app.services.monai_service import MonaiService
from backend.app.utils.exceptions import ReportGenerationError


class ReportGenerator:
    """Orchestrates the report generation workflow."""

    def __init__(
        self,
        kheops_client: IKheopsClient = None,
        dicom_parser: DicomParserService = None,
        diagnosis_provider: IDiagnosisProvider = None,
        report_generator: IReportGenerator = None,
    ):
        """
        Initialize report generator with dependencies.

        Args:
            kheops_client: Kheops client for DICOM retrieval
            dicom_parser: DICOM parser service
            diagnosis_provider: MONAI service for diagnosis
            report_generator: LLM service for report generation
        """
        self.kheops_client = kheops_client or KheopsService()
        self.dicom_parser = dicom_parser or DicomParserService()
        self.diagnosis_provider = diagnosis_provider or MonaiService()
        self.report_generator = report_generator or LLMService()

    def generate_report_from_album(self, album_token: str, study_id: str, series_id: str = None) -> Dict[str, Any]:
        """
        Generate report from Kheops album study.

        Args:
            album_token: Album token for authentication
            study_id: ID of the study
            series_id: Optional series ID (uses first series if not provided)

        Returns:
            Dictionary with report and metadata

        Raises:
            ReportGenerationError: If generation fails
        """
        try:
            series_list = self.kheops_client.fetch_series(album_token, study_id)

            if not series_list:
                raise ReportGenerationError(f"No series found for study {study_id}")

            target_series = series_list[0] if series_id is None else next((s for s in series_list if s.series_id == series_id), None)

            if target_series is None:
                raise ReportGenerationError(f"Series {series_id} not found")

            # Fetch instances from the series
            instance_ids = self.kheops_client.fetch_instances(
                album_token, study_id, target_series.series_id
            )

            if not instance_ids:
                raise ReportGenerationError(f"No instances found in series {target_series.series_id}")

            # Download the first instance
            instance_id = instance_ids[0]
            dicom_bytes = self.kheops_client.download_instance(
                album_token, study_id, target_series.series_id, instance_id
            )

            return self._process_dicom_to_report(dicom_bytes)
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate report from album: {str(e)}") from e

    def generate_report_from_dicom(self, dicom_bytes: bytes) -> Dict[str, Any]:
        """
        Generate report from DICOM file bytes.

        Args:
            dicom_bytes: Raw DICOM file bytes

        Returns:
            Dictionary with report and metadata

        Raises:
            ReportGenerationError: If generation fails
        """
        try:
            return self._process_dicom_to_report(dicom_bytes)
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate report from DICOM: {str(e)}") from e

    def _process_dicom_to_report(self, dicom_bytes: bytes) -> Dict[str, Any]:
        """
        Process DICOM bytes through the full pipeline.

        Args:
            dicom_bytes: Raw DICOM file bytes

        Returns:
            Dictionary with report and metadata
        """
        dicom_data = self.dicom_parser.parse_dicom_file(dicom_bytes)
        pixel_array = self.dicom_parser.extract_pixel_array(dicom_data)
        normalized_image = self.dicom_parser.normalize_image(pixel_array)

        image_tensor = self.diagnosis_provider.preprocess_image(normalized_image)
        diagnosis = self.diagnosis_provider.run_inference(image_tensor)

        prompt = self.report_generator.create_prompt(diagnosis)
        raw_report = self.report_generator.generate_report(prompt)
        clinical_report = self.report_generator.format_report(raw_report)

        return {
            "report": clinical_report,
            "diagnosis": diagnosis,
            "dicom_metadata": {
                "study_id": dicom_data.study_id,
                "series_id": dicom_data.series_id,
                "patient_id": dicom_data.patient_id,
                "patient_name": dicom_data.patient_name,
            },
        }
