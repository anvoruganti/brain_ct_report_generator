"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StudyResponse(BaseModel):
    """Response schema for a study."""

    study_id: str = Field(..., description="Study instance UID")
    study_date: Optional[str] = Field(None, description="Study date")
    study_description: Optional[str] = Field(None, description="Study description")
    patient_id: Optional[str] = Field(None, description="Patient ID")
    patient_name: Optional[str] = Field(None, description="Patient name")


class SeriesResponse(BaseModel):
    """Response schema for a series."""

    series_id: str = Field(..., description="Series instance UID")
    study_id: str = Field(..., description="Study instance UID")
    series_description: Optional[str] = Field(None, description="Series description")
    modality: Optional[str] = Field(None, description="Modality")
    instance_count: Optional[int] = Field(None, description="Number of instances")


class StudiesResponse(BaseModel):
    """Response schema for list of studies."""

    studies: List[StudyResponse] = Field(..., description="List of studies")


class SeriesListResponse(BaseModel):
    """Response schema for list of series."""

    series: List[SeriesResponse] = Field(..., description="List of series")


class AbnormalityItem(BaseModel):
    """Schema for an abnormality."""

    name: str = Field(..., description="Abnormality name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class DiagnosisResponse(BaseModel):
    """Response schema for diagnosis results."""

    abnormalities: List[str] = Field(..., description="List of detected abnormalities")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores by class")
    findings: Dict[str, Any] = Field(..., description="Detailed findings")
    timestamp: datetime = Field(default_factory=datetime.now, description="Diagnosis timestamp")


class ClinicalReportResponse(BaseModel):
    """Response schema for clinical report."""

    clinical_history: Optional[str] = Field(None, description="Clinical history")
    findings: Optional[str] = Field(None, description="Findings")
    impression: Optional[str] = Field(None, description="Impression")
    recommendations: Optional[str] = Field(None, description="Recommendations")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation timestamp")


class ReportResponse(BaseModel):
    """Response schema for complete report."""

    report: ClinicalReportResponse = Field(..., description="Clinical report")
    diagnosis: DiagnosisResponse = Field(..., description="Diagnosis results")
    dicom_metadata: Dict[str, Optional[str]] = Field(..., description="DICOM metadata")


class InferenceFromKheopsRequest(BaseModel):
    """Request schema for inference from Kheops."""

    album_token: str = Field(..., description="Album token for authentication")
    study_id: str = Field(..., description="Study instance UID")
    series_id: Optional[str] = Field(None, description="Optional series instance UID")


class InferenceFromDicomRequest(BaseModel):
    """Request schema for inference from uploaded DICOM."""

    dicom_file: bytes = Field(..., description="DICOM file bytes")


class HealthResponse(BaseModel):
    """Response schema for health check."""

    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
