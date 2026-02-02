"""FastAPI route definitions."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List

logger = logging.getLogger(__name__)

from backend.app.config import get_settings
from backend.app.dependencies import (
    get_kheops_service,
    get_report_generator,
)
from backend.app.models.schemas import (
    HealthResponse,
    StudiesResponse,
    SeriesListResponse,
    ReportResponse,
    InferenceFromKheopsRequest,
    StudyResponse,
    SeriesResponse,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return HealthResponse()


@router.get("/kheops/studies", response_model=StudiesResponse)
async def get_studies(
    album_token: str,
    kheops_service: Any = Depends(get_kheops_service),  # type: ignore
) -> StudiesResponse:
    """
    Get all studies from a Kheops album.
    
    NOTE: Kheops integration is disabled for PoC. This endpoint is kept for future use.
    For PoC, use /api/inference/from-dicom with local file upload.
    """
    settings = get_settings()
    if not settings.enable_kheops:
        raise HTTPException(
            status_code=503,
            detail="Kheops integration is disabled for PoC. Please use /api/inference/from-dicom with local file upload."
        )
    """
    Get all studies from a Kheops album.

    Args:
        album_token: Album token for authentication
        kheops_service: Kheops service (injected)

    Returns:
        List of studies

    Raises:
        HTTPException: If API request fails
    """
    try:
        studies = kheops_service.fetch_studies(album_token)
        study_responses = [
            StudyResponse(
                study_id=study.study_id,
                study_date=study.study_date,
                study_description=study.study_description,
                patient_id=study.patient_id,
                patient_name=study.patient_name,
            )
            for study in studies
        ]
        return StudiesResponse(studies=study_responses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch studies: {str(e)}")


@router.get("/kheops/studies/{study_id}/series", response_model=SeriesListResponse)
async def get_series(
    study_id: str,
    album_token: str,
    kheops_service: Any = Depends(get_kheops_service),  # type: ignore
) -> SeriesListResponse:
    """
    Get all series within a study.
    
    NOTE: Kheops integration is disabled for PoC. This endpoint is kept for future use.
    For PoC, use /api/inference/from-dicom with local file upload.

    Args:
        study_id: Study instance UID
        album_token: Album token for authentication
        kheops_service: Kheops service (injected)

    Returns:
        List of series

    Raises:
        HTTPException: If API request fails
    """
    settings = get_settings()
    if not settings.enable_kheops:
        raise HTTPException(
            status_code=503,
            detail="Kheops integration is disabled for PoC. Please use /api/inference/from-dicom with local file upload."
        )
    try:
        series_list = kheops_service.fetch_series(album_token, study_id)
        series_responses = [
            SeriesResponse(
                series_id=series.series_id,
                study_id=series.study_id,
                series_description=series.series_description,
                modality=series.modality,
                instance_count=series.instance_count,
            )
            for series in series_list
        ]
        return SeriesListResponse(series=series_responses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch series: {str(e)}")


@router.post("/inference/from-kheops", response_model=ReportResponse)
async def generate_report_from_kheops(
    request: InferenceFromKheopsRequest,
    report_generator: Any = Depends(get_report_generator),  # type: ignore
) -> ReportResponse:
    """
    Generate report from Kheops study.
    
    NOTE: Kheops integration is disabled for PoC. This endpoint is kept for future use.
    For PoC, use /api/inference/from-dicom with local file upload.

    Args:
        request: Request with album token and study ID
        report_generator: Report generator (injected)

    Returns:
        Generated report with diagnosis

    Raises:
        HTTPException: If report generation fails
    """
    settings = get_settings()
    if not settings.enable_kheops:
        raise HTTPException(
            status_code=503,
            detail="Kheops integration is disabled for PoC. Please use /api/inference/from-dicom with local file upload."
        )
    try:
        logger.info(f"Generating report for study {request.study_id}, series {request.series_id}")
        result = report_generator.generate_report_from_album(
            request.album_token,
            request.study_id,
            request.series_id,
        )

        from backend.app.models.schemas import ClinicalReportResponse, DiagnosisResponse

        return ReportResponse(
            report=ClinicalReportResponse(
                clinical_history=result["report"].clinical_history,
                findings=result["report"].findings,
                impression=result["report"].impression,
                recommendations=result["report"].recommendations,
                generated_at=result["report"].generated_at,
            ),
            diagnosis=DiagnosisResponse(
                abnormalities=result["diagnosis"].abnormalities,
                confidence_scores=result["diagnosis"].confidence_scores,
                findings=result["diagnosis"].findings,
                timestamp=result["diagnosis"].timestamp,
            ),
            dicom_metadata=result["dicom_metadata"],
        )
    except Exception as e:
        logger.exception(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.post("/inference/from-dicom", response_model=ReportResponse)
async def generate_report_from_dicom(
    dicom_files: List[UploadFile] = File(...),
    report_generator: Any = Depends(get_report_generator),  # type: ignore
) -> ReportResponse:
    """
    Generate report from uploaded DICOM file(s).
    
    Supports both single file and multiple files (series).
    When multiple files are uploaded, generates an aggregated report.

    Args:
        dicom_files: Uploaded DICOM file(s) - can be single file or multiple files
        report_generator: Report generator (injected)

    Returns:
        Generated report with diagnosis

    Raises:
        HTTPException: If report generation fails
    """
    try:
        if not dicom_files:
            raise HTTPException(status_code=400, detail="No DICOM files provided")
        
        logger.info(f"Processing {len(dicom_files)} DICOM file(s)")
        
        # Read all uploaded files
        dicom_bytes_list = []
        for dicom_file in dicom_files:
            dicom_bytes = await dicom_file.read()
            dicom_bytes_list.append(dicom_bytes)

        # Process single file or series
        if len(dicom_bytes_list) == 1:
            logger.info("Processing single DICOM file")
            result = report_generator.generate_report_from_dicom(dicom_bytes_list[0])
        else:
            logger.info(f"Processing DICOM series with {len(dicom_bytes_list)} images")
            result = report_generator.generate_report_from_dicom_series(dicom_bytes_list)

        from backend.app.models.schemas import ClinicalReportResponse, DiagnosisResponse

        return ReportResponse(
            report=ClinicalReportResponse(
                clinical_history=result["report"].clinical_history,
                findings=result["report"].findings,
                impression=result["report"].impression,
                recommendations=result["report"].recommendations,
                generated_at=result["report"].generated_at,
            ),
            diagnosis=DiagnosisResponse(
                abnormalities=result["diagnosis"].abnormalities,
                confidence_scores=result["diagnosis"].confidence_scores,
                findings=result["diagnosis"].findings,
                timestamp=result["diagnosis"].timestamp,
            ),
            dicom_metadata=result["dicom_metadata"],
        )
    except Exception as e:
        logger.exception(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
