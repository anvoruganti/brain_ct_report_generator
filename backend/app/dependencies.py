"""Dependency injection for FastAPI."""

import os
import logging

from backend.app.config import get_settings
from backend.app.services.dicom_parser import DicomParserService
from backend.app.services.kheops_service import KheopsService
from backend.app.services.llm_service import LLMService
from backend.app.services.monai_service import MonaiService
from backend.app.services.report_generator import ReportGenerator
from backend.app.utils.exceptions import ModelLoadError

logger = logging.getLogger(__name__)


def get_kheops_service() -> KheopsService:
    """
    Get Kheops service instance.

    Returns:
        KheopsService instance
    """
    return KheopsService()


def get_dicom_parser() -> DicomParserService:
    """
    Get DICOM parser service instance.

    Returns:
        DicomParserService instance
    """
    return DicomParserService()


def get_monai_service() -> MonaiService:
    """
    Get MONAI service instance and load model if available.

    Returns:
        MonaiService instance with model loaded (if model file exists)
    """
    settings = get_settings()
    service = MonaiService()
    
    # Try to load model if path exists
    model_path = settings.monai_model_path
    if os.path.exists(model_path):
        try:
            logger.info(f"Loading MONAI model from {model_path}")
            service.load_model(model_path)
            logger.info("MONAI model loaded successfully")
        except ModelLoadError as e:
            logger.warning(f"Failed to load MONAI model: {e}. Model inference will not be available.")
    else:
        logger.warning(
            f"MONAI model file not found at {model_path}. "
            "Model inference will not be available. "
            "For PoC/testing, the system will use mock diagnosis results."
        )
    
    return service


def get_llm_service() -> LLMService:
    """
    Get LLM service instance.

    Returns:
        LLMService instance
    """
    return LLMService()


def get_report_generator() -> ReportGenerator:
    """
    Get report generator instance with dependencies.

    Returns:
        ReportGenerator instance
    """
    return ReportGenerator(
        kheops_client=get_kheops_service(),
        dicom_parser=get_dicom_parser(),
        diagnosis_provider=get_monai_service(),
        report_generator=get_llm_service(),
    )
