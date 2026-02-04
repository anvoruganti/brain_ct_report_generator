"""Report generator service that orchestrates the end-to-end workflow."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from backend.app.models.domain import ClinicalReport, DiagnosisResult
from backend.app.services.dicom_parser import DicomParserService
from backend.app.services.interfaces import IDiagnosisProvider, IKheopsClient, IReportGenerator
from backend.app.services.kheops_service import KheopsService
from backend.app.services.llm_service import LLMService
from backend.app.services.monai_service import MonaiService
from backend.app.utils.exceptions import ReportGenerationError
from backend.app.config import get_settings

logger = logging.getLogger(__name__)


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
        self.settings = get_settings()

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
        Generate aggregated report from multiple DICOM files (series) using parallel processing.
        
        Simplified PoC approach:
        1. Process all DICOM files in parallel using ThreadPoolExecutor
        2. Aggregate all diagnoses into a single comprehensive diagnosis
        3. Generate ONE final report from aggregated diagnosis (fast, simple for PoC)

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
            logger.info(f"Processing {len(dicom_files)} DICOM files in parallel (PoC mode)")
            
            # Step 1: Process all DICOM files in parallel (fast!)
            diagnoses, all_metadata = self._process_files_parallel(dicom_files)
            
            if not diagnoses:
                raise ReportGenerationError("Failed to process any DICOM files")

            logger.info(f"Successfully processed {len(diagnoses)}/{len(dicom_files)} files")

            # Step 2: Aggregate all diagnoses into one comprehensive diagnosis
            logger.info("Aggregating all diagnoses...")
            aggregated_diagnosis = self._aggregate_diagnoses(diagnoses)

            # Step 3: Generate ONE final report from aggregated diagnosis (simple & fast for PoC)
            logger.info("Generating clinical report from aggregated diagnosis...")
            prompt = self.report_generator.create_prompt(aggregated_diagnosis)
            raw_report = self.report_generator.generate_report(prompt)
            clinical_report = self.report_generator.format_report(raw_report)

            # Use metadata from first successfully processed file
            primary_metadata = all_metadata[0] if all_metadata else {}

            result = {
                "report": clinical_report,
                "diagnosis": aggregated_diagnosis,
                "dicom_metadata": {
                    "study_id": primary_metadata.get("study_id"),
                    "series_id": primary_metadata.get("series_id"),
                    "patient_id": primary_metadata.get("patient_id"),
                    "patient_name": primary_metadata.get("patient_name"),
                    "total_images_processed": str(len(diagnoses)),
                    "total_images_uploaded": str(len(dicom_files)),
                },
                "image_metadata": all_metadata,
            }
            
            logger.info(f"✅ Successfully generated report from {len(dicom_files)} files")
            return result
        except Exception as e:
            logger.exception(f"Error generating report from DICOM series: {str(e)}")
            raise ReportGenerationError(f"Failed to generate report from DICOM series: {str(e)}") from e
    
    def _parse_and_preprocess_file(self, dicom_bytes: bytes, file_index: int, total_files: int) -> Tuple[Any, Dict[str, Any], Exception]:
        """
        Parse DICOM file and preprocess image (without running inference).
        
        Includes hard sanity checks to pinpoint failures.
        
        Args:
            dicom_bytes: Raw DICOM file bytes
            file_index: Index of the file in the series (0-based)
            total_files: Total number of files being processed
            
        Returns:
            Tuple of (preprocessed_tensor, metadata dict, Exception if any)
        """
        from io import BytesIO
        import pydicom
        
        try:
            # Sanity check 1: Empty bytes
            if not dicom_bytes:
                raise ValueError("Empty/None DICOM bytes received")
            
            if len(dicom_bytes) < 132:
                raise ValueError(f"DICOM file too small ({len(dicom_bytes)} bytes), likely corrupted")
            
            # Sanity check 2: Read DICOM header
            try:
                dicom_file = pydicom.dcmread(BytesIO(dicom_bytes), force=True)
            except Exception as read_error:
                raise ValueError(f"Failed to read DICOM header: {str(read_error)}") from read_error
            
            # Log DICOM metadata for debugging
            sop_uid = getattr(dicom_file, "SOPInstanceUID", None)
            transfer_syntax = None
            if hasattr(dicom_file, "file_meta") and dicom_file.file_meta:
                transfer_syntax = getattr(dicom_file.file_meta, "TransferSyntaxUID", None)
            has_pixel = hasattr(dicom_file, "PixelData")
            
            logger.info(
                f"DICOM file {file_index + 1}/{total_files}: "
                f"SOP={sop_uid[:20] if sop_uid else 'None'}... "
                f"TS={transfer_syntax} "
                f"hasPixel={has_pixel} "
                f"size={len(dicom_bytes)} bytes"
            )
            
            # Parse using our parser (handles metadata extraction)
            dicom_data = self.dicom_parser.parse_dicom_file(dicom_bytes)
            
            # Sanity check 3: Extract pixel array (this is where compression errors occur)
            try:
                pixel_array = self.dicom_parser.extract_pixel_array(dicom_data)
            except Exception as pixel_error:
                # This is the key decoder test - if it fails here, we know it's a pixel decoding issue
                logger.error(
                    f"File {file_index + 1}/{total_files} pixel extraction failed: {type(pixel_error).__name__}: {str(pixel_error)}"
                )
                raise
            
            if pixel_array is None or pixel_array.size == 0:
                raise ValueError("Pixel array is empty after extraction")
            
            # Normalize and preprocess
            normalized_image = self.dicom_parser.normalize_image(pixel_array)
            image_tensor = self.diagnosis_provider.preprocess_image(normalized_image)
            
            metadata = {
                "study_id": dicom_data.study_id,
                "series_id": dicom_data.series_id,
                "instance_id": dicom_data.instance_id,
                "patient_id": dicom_data.patient_id,
                "patient_name": dicom_data.patient_name,
                "image_index": file_index + 1,
            }
            
            logger.debug(f"File {file_index + 1}/{total_files} processed successfully")
            return image_tensor, metadata, None
            
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_msg = str(e)
            tb_lines = traceback.format_exc().splitlines()
            
            logger.error(f"File {file_index + 1}/{total_files} failed: {error_type}: {error_msg}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            
            return None, None, e
    
    def _process_files_parallel(self, dicom_files: List[bytes]) -> Tuple[List[DiagnosisResult], List[Dict[str, Any]]]:
        """
        Process multiple DICOM files in parallel using ThreadPoolExecutor with batch inference.
        
        This method:
        1. Parses and preprocesses files in parallel (I/O bound)
        2. Groups preprocessed images into batches
        3. Runs batch inference (much faster than individual calls, especially on MPS/CUDA)
        
        Args:
            dicom_files: List of raw DICOM file bytes
            
        Returns:
            Tuple of (list of diagnoses, list of metadata dicts)
        """
        max_workers = self.settings.max_workers
        batch_size = self.settings.monai_batch_size
        
        logger.info(f"Processing {len(dicom_files)} files: parsing in parallel ({max_workers} workers), inference in batches ({batch_size} per batch)")
        
        # Step 1: Parse and preprocess all files in parallel (I/O bound)
        preprocessed_data = []
        all_metadata = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self._parse_and_preprocess_file, dicom_bytes, idx, len(dicom_files)): idx
                for idx, dicom_bytes in enumerate(dicom_files)
            }
            
            # Collect results as they complete
            results = [None] * len(dicom_files)
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    image_tensor, metadata, error = future.result()
                    if error is None and image_tensor is not None:
                        results[idx] = (image_tensor, metadata)
                        logger.debug(f"File {idx + 1}/{len(dicom_files)} parsed and preprocessed")
                    else:
                        logger.warning(f"File {idx + 1}/{len(dicom_files)} failed: {error}")
                except Exception as e:
                    logger.warning(f"File {idx + 1}/{len(dicom_files)} raised exception: {str(e)}")
            
            # Reconstruct ordered results
            for result in results:
                if result is not None:
                    image_tensor, metadata = result
                    preprocessed_data.append(image_tensor)
                    all_metadata.append(metadata)
        
        if not preprocessed_data:
            logger.warning("No files successfully preprocessed")
            return [], []
        
        logger.info(f"Successfully preprocessed {len(preprocessed_data)}/{len(dicom_files)} files")
        
        # Step 2: Run batch inference (much faster than individual calls)
        diagnoses = []
        total_batches = (len(preprocessed_data) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(preprocessed_data), batch_size):
            batch_end = min(batch_idx + batch_size, len(preprocessed_data))
            batch_tensors = preprocessed_data[batch_idx:batch_end]
            
            logger.debug(f"Running batch inference: batch {batch_idx // batch_size + 1}/{total_batches} ({len(batch_tensors)} images)")
            
            # Run batch inference (much faster!)
            batch_diagnoses = self.diagnosis_provider.run_inference_batch(batch_tensors)
            diagnoses.extend(batch_diagnoses)
        
        logger.info(f"✅ Successfully processed {len(diagnoses)}/{len(dicom_files)} files with batch inference")
        return diagnoses, all_metadata

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
