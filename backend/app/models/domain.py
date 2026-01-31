"""Domain models for the application."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Study:
    """Represents a DICOM study."""

    study_id: str
    study_date: Optional[str] = None
    study_description: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None


@dataclass
class Series:
    """Represents a DICOM series."""

    series_id: str
    study_id: str
    series_description: Optional[str] = None
    modality: Optional[str] = None
    instance_count: Optional[int] = None


@dataclass
class DicomData:
    """Represents parsed DICOM data."""

    study_id: Optional[str] = None
    series_id: Optional[str] = None
    instance_id: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    study_date: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata dict if None."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DiagnosisResult:
    """Represents diagnosis results from MONAI model."""

    abnormalities: List[str]
    confidence_scores: Dict[str, float]
    findings: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        """Initialize timestamp if None."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ClinicalReport:
    """Represents a formatted clinical report."""

    clinical_history: Optional[str] = None
    findings: Optional[str] = None
    impression: Optional[str] = None
    recommendations: Optional[str] = None
    generated_at: datetime = None

    def __post_init__(self):
        """Initialize generated_at if None."""
        if self.generated_at is None:
            self.generated_at = datetime.now()
