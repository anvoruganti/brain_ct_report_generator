"""Custom exceptions for the application."""


class KheopsAPIError(Exception):
    """Raised when Kheops API request fails."""

    pass


class DicomParseError(Exception):
    """Raised when DICOM parsing fails."""

    pass


class ModelLoadError(Exception):
    """Raised when model loading fails."""

    pass


class LLMInitializationError(Exception):
    """Raised when LLM initialization fails."""

    pass


class ReportGenerationError(Exception):
    """Raised when report generation fails."""

    pass
