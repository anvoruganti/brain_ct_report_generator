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


@router.post("/api/debug/dicom")
async def debug_dicom(files: List[UploadFile] = File(...)):
    """
    Debug endpoint to test DICOM file decoding without running full pipeline.
    
    Tests up to 5 files and returns metadata about their structure.
    Useful for verifying pixel decoding libraries are installed correctly.
    
    Args:
        files: Uploaded DICOM files (up to 5 will be tested)
        
    Returns:
        Dictionary with decoding results and metadata
    """
    from io import BytesIO
    import pydicom
    
    results = []
    tested_files = files[:5]  # Test up to 5 files
    
    for f in tested_files:
        try:
            b = await f.read()
            
            if not b:
                results.append({
                    "name": f.filename,
                    "error": "Empty file",
                    "ok": False,
                })
                continue
            
            # Try to read DICOM
            try:
                ds = pydicom.dcmread(BytesIO(b), force=True)
            except Exception as read_error:
                results.append({
                    "name": f.filename,
                    "error": f"DICOM read failed: {str(read_error)}",
                    "ok": False,
                })
                continue
            
            # Extract metadata
            transfer_syntax = None
            if hasattr(ds, "file_meta") and ds.file_meta:
                transfer_syntax = str(getattr(ds.file_meta, "TransferSyntaxUID", ""))
            
            has_pixel = hasattr(ds, "PixelData")
            rows = int(getattr(ds, "Rows", 0))
            cols = int(getattr(ds, "Columns", 0))
            sop_uid = str(getattr(ds, "SOPInstanceUID", ""))
            
            # Try pixel array extraction (this is the key test)
            pixel_test = {"ok": False, "error": None}
            if has_pixel:
                try:
                    arr = ds.pixel_array
                    pixel_test = {
                        "ok": True,
                        "shape": list(arr.shape) if arr is not None else None,
                        "dtype": str(arr.dtype) if arr is not None else None,
                    }
                except Exception as pixel_error:
                    pixel_test = {
                        "ok": False,
                        "error": f"{type(pixel_error).__name__}: {str(pixel_error)}",
                    }
            
            results.append({
                "name": f.filename,
                "ok": True,
                "transfer_syntax": transfer_syntax,
                "has_pixel": has_pixel,
                "pixel_test": pixel_test,
                "rows": rows,
                "cols": cols,
                "sop_uid": sop_uid[:30] + "..." if len(sop_uid) > 30 else sop_uid,
                "file_size": len(b),
            })
            
        except Exception as e:
            results.append({
                "name": f.filename,
                "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
                "ok": False,
            })
    
    return {
        "ok": True,
        "files_tested": len(tested_files),
        "samples": results,
    }


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
    # #region agent log
    import json
    import time
    with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"routes.py:191","message":"API route entry","data":{"file_count":len(dicom_files) if dicom_files else 0},"timestamp":int(time.time()*1000)})+'\n')
    # #endregion
    try:
        if not dicom_files:
            raise HTTPException(status_code=400, detail="No DICOM files provided")
        
        logger.info(f"Processing {len(dicom_files)} DICOM file(s)")
        
        # Read all uploaded files
        # Handle both individual files and ZIP archives
        dicom_bytes_list = []
        
        for idx, dicom_file in enumerate(dicom_files):
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"routes.py:221","message":"Reading file","data":{"file_index":idx,"filename":dicom_file.filename},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            
            dicom_bytes = await dicom_file.read()
            
            # Check if it's a ZIP file (KHEOPS exports are often ZIP)
            if dicom_file.filename and dicom_file.filename.lower().endswith('.zip'):
                import zipfile
                import tempfile
                from pathlib import Path
                from backend.app.utils.dicom_utils import collect_all_files_recursively, looks_like_dicom
                
                logger.info(f"Detected ZIP file: {dicom_file.filename}, extracting...")
                
                # Extract ZIP to temporary directory
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)
                    zip_path = tmp_path / dicom_file.filename
                    zip_path.write_bytes(dicom_bytes)
                    
                    # Extract ZIP
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(tmp_path)
                    
                    # Recursively collect all files (handles DICOM/0/* structure)
                    all_files = collect_all_files_recursively(tmp_path)
                    logger.info(f"Found {len(all_files)} files in ZIP archive")
                    
                    # Read and filter DICOM files
                    for file_path in all_files:
                        try:
                            file_bytes = file_path.read_bytes()
                            if looks_like_dicom(file_bytes):
                                dicom_bytes_list.append(file_bytes)
                                logger.debug(f"Added DICOM file from ZIP: {file_path.name}")
                        except Exception as e:
                            logger.warning(f"Failed to read file {file_path.name} from ZIP: {str(e)}")
                            continue
                
                logger.info(f"Extracted {len(dicom_bytes_list)} DICOM files from ZIP")
            else:
                # Regular file upload
                # #region agent log
                with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"routes.py:223","message":"File read complete","data":{"file_index":idx,"bytes_length":len(dicom_bytes)},"timestamp":int(time.time()*1000)})+'\n')
                # #endregion
                
                # Validate it looks like DICOM
                from backend.app.utils.dicom_utils import looks_like_dicom
                if looks_like_dicom(dicom_bytes):
                    dicom_bytes_list.append(dicom_bytes)
                else:
                    logger.warning(f"File {dicom_file.filename} doesn't appear to be DICOM format, skipping")

        # Process single file or series
        try:
            if len(dicom_bytes_list) == 1:
                # #region agent log
                with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"routes.py:225","message":"Processing single file","data":{},"timestamp":int(time.time()*1000)})+'\n')
                # #endregion
                logger.info("Processing single DICOM file")
                result = report_generator.generate_report_from_dicom(dicom_bytes_list[0])
            else:
                # #region agent log
                with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"routes.py:228","message":"Processing series","data":{"file_count":len(dicom_bytes_list)},"timestamp":int(time.time()*1000)})+'\n')
                # #endregion
                logger.info(f"Processing DICOM series with {len(dicom_bytes_list)} images")
                result = report_generator.generate_report_from_dicom_series(dicom_bytes_list)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            error_type = type(e).__name__
            error_msg = str(e)
            
            logger.error(f"Inference failed: {error_type}: {error_msg}")
            logger.error(f"Full traceback:\n{tb}")
            
            # Return detailed error information
            raise HTTPException(
                status_code=500,
                detail={
                    "error": error_msg,
                    "type": error_type,
                    "traceback_tail": tb.splitlines()[-40:],  # Last 40 lines of traceback
                },
            )

        # #region agent log
        with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:232","message":"Building response schema","data":{"has_report":'report' in result,"has_diagnosis":'diagnosis' in result,"has_metadata":'dicom_metadata' in result},"timestamp":int(time.time()*1000)})+'\n')
        # #endregion

        from backend.app.models.schemas import ClinicalReportResponse, DiagnosisResponse

        # #region agent log
        try:
            report_obj = result["report"]
            diagnosis_obj = result["diagnosis"]
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:262","message":"Before schema creation","data":{"report_type":type(report_obj).__name__,"diagnosis_type":type(diagnosis_obj).__name__,"has_clinical_history":hasattr(report_obj,'clinical_history'),"has_findings":hasattr(report_obj,'findings')},"timestamp":int(time.time()*1000)})+'\n')
        except Exception as schema_err:
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:265","message":"Schema access error","data":{"error":str(schema_err)},"timestamp":int(time.time()*1000)})+'\n')
            raise
        # #endregion

        try:
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:273","message":"Creating ClinicalReportResponse","data":{},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            clinical_report_response = ClinicalReportResponse(
                clinical_history=result["report"].clinical_history,
                findings=result["report"].findings,
                impression=result["report"].impression,
                recommendations=result["report"].recommendations,
                generated_at=result["report"].generated_at,
            )
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:281","message":"Creating DiagnosisResponse","data":{},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            diagnosis_response = DiagnosisResponse(
                abnormalities=result["diagnosis"].abnormalities,
                confidence_scores=result["diagnosis"].confidence_scores,
                findings=result["diagnosis"].findings,
                timestamp=result["diagnosis"].timestamp,
            )
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:288","message":"Creating ReportResponse","data":{},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            response = ReportResponse(
                report=clinical_report_response,
                diagnosis=diagnosis_response,
                dicom_metadata=result["dicom_metadata"],
            )
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:295","message":"ReportResponse created successfully","data":{},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
        except Exception as schema_err:
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"routes.py:298","message":"Schema creation exception","data":{"error_type":type(schema_err).__name__,"error_msg":str(schema_err)},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            raise
        # #region agent log
        with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"routes.py:252","message":"API route exit success","data":{},"timestamp":int(time.time()*1000)})+'\n')
        # #endregion
        return response
    except HTTPException:
        # Re-raise HTTPException as-is (already has detailed error info)
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        error_type = type(e).__name__
        error_msg = str(e)
        
        # #region agent log
        with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"routes.py:255","message":"API route exception","data":{"error_type":error_type,"error_msg":error_msg},"timestamp":int(time.time()*1000)})+'\n')
        # #endregion
        
        logger.exception(f"Error generating report: {error_type}: {error_msg}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "type": error_type,
                "traceback_tail": tb.splitlines()[-40:],
            },
        )
