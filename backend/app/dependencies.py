"""Dependency injection for FastAPI."""

from backend.app.services.dicom_parser import DicomParserService
from backend.app.services.kheops_service import KheopsService
from backend.app.services.llm_service import LLMService
from backend.app.services.monai_service import MonaiService
from backend.app.services.report_generator import ReportGenerator


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
    Get MONAI service instance.

    Returns:
        MonaiService instance
    """
    return MonaiService()


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
