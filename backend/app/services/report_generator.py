"""Report generator service that orchestrates the end-to-end workflow."""

from typing import Dict, Any, List
from collections import defaultdict

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
            instances = self.kheops_client.fetch_instances(
                album_token, study_id, target_series.series_id
            )

            if not instances:
                raise ReportGenerationError(f"No instances found in series {target_series.series_id}")

            # Download the first instance
            first_instance = instances[0]
            instance_id = first_instance["instance_id"]
            instance_url = first_instance.get("instance_url")
            dicom_bytes = self.kheops_client.download_instance(
                album_token, study_id, target_series.series_id, instance_id, instance_url
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

    def generate_report_from_dicom_series(self, dicom_files: List[bytes]) -> Dict[str, Any]:
        """
        Generate aggregated report from multiple DICOM files (series).

        Args:
            dicom_files: List of raw DICOM file bytes

        Returns:
            Dictionary with aggregated report and metadata

        Raises:
            ReportGenerationError: If generation fails
        """
        if not dicom_files:
            raise ReportGenerationError("No DICOM files provided")

        try:
            # Process all DICOM files and collect diagnoses
            diagnoses = []
            all_metadata = []
            
            for idx, dicom_bytes in enumerate(dicom_files):
                try:
                    dicom_data = self.dicom_parser.parse_dicom_file(dicom_bytes)
                    pixel_array = self.dicom_parser.extract_pixel_array(dicom_data)
                    normalized_image = self.dicom_parser.normalize_image(pixel_array)

                    image_tensor = self.diagnosis_provider.preprocess_image(normalized_image)
                    diagnosis = self.diagnosis_provider.run_inference(image_tensor)
                    diagnoses.append(diagnosis)
                    all_metadata.append({
                        "study_id": dicom_data.study_id,
                        "series_id": dicom_data.series_id,
                        "instance_id": dicom_data.instance_id,
                        "patient_id": dicom_data.patient_id,
                        "patient_name": dicom_data.patient_name,
                        "image_index": idx + 1,
                    })
                except Exception as e:
                    # Log error but continue with other images
                    continue

            if not diagnoses:
                raise ReportGenerationError("Failed to process any DICOM files")

            # Aggregate diagnoses
            aggregated_diagnosis = self._aggregate_diagnoses(diagnoses)

            # Generate report from aggregated diagnosis
            prompt = self.report_generator.create_prompt(aggregated_diagnosis)
            raw_report = self.report_generator.generate_report(prompt)
            clinical_report = self.report_generator.format_report(raw_report)

            # Use metadata from first successfully processed file
            primary_metadata = all_metadata[0] if all_metadata else {}

            return {
                "report": clinical_report,
                "diagnosis": aggregated_diagnosis,
                "dicom_metadata": {
                    "study_id": primary_metadata.get("study_id"),
                    "series_id": primary_metadata.get("series_id"),
                    "patient_id": primary_metadata.get("patient_id"),
                    "patient_name": primary_metadata.get("patient_name"),
                    "total_images_processed": len(diagnoses),
                    "total_images_uploaded": len(dicom_files),
                },
                "image_metadata": all_metadata,
            }
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate report from DICOM series: {str(e)}") from e

    def _aggregate_diagnoses(self, diagnoses: List[DiagnosisResult]) -> DiagnosisResult:
        """
        Aggregate multiple diagnosis results into a single comprehensive diagnosis.

        Args:
            diagnoses: List of diagnosis results from multiple images

        Returns:
            Aggregated DiagnosisResult
        """
        from datetime import datetime
        from collections import Counter

        # Aggregate abnormalities (union of all abnormalities)
        all_abnormalities = []
        for diagnosis in diagnoses:
            all_abnormalities.extend(diagnosis.abnormalities)
        
        # Count occurrences and keep unique abnormalities
        abnormality_counts = Counter(all_abnormalities)
        unique_abnormalities = list(abnormality_counts.keys())

        # Aggregate confidence scores (average across all images)
        aggregated_confidence = defaultdict(float)
        for diagnosis in diagnoses:
            for key, value in diagnosis.confidence_scores.items():
                aggregated_confidence[key] += value
        
        # Average the confidence scores
        num_images = len(diagnoses)
        for key in aggregated_confidence:
            aggregated_confidence[key] /= num_images

        # Aggregate findings (combine all findings)
        aggregated_findings = {
            "total_images_analyzed": num_images,
            "abnormality_frequency": dict(abnormality_counts),
            "per_image_findings": [
                {
                    "abnormalities": diag.abnormalities,
                    "confidence_scores": diag.confidence_scores,
                    "findings": diag.findings,
                }
                for diag in diagnoses
            ],
        }

        return DiagnosisResult(
            abnormalities=unique_abnormalities,
            confidence_scores=dict(aggregated_confidence),
            findings=aggregated_findings,
            timestamp=datetime.now(),
        )

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
