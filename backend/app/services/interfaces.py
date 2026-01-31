"""Abstract base classes (interfaces) following SOLID principles."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

from backend.app.models.domain import DiagnosisResult, DicomData, Series, Study

if TYPE_CHECKING:
    import numpy as np
    import torch
    from backend.app.models.domain import ClinicalReport


class IKheopsClient(ABC):
    """Interface for Kheops DICOM client following Interface Segregation Principle."""

    @abstractmethod
    def fetch_studies(self, album_token: str) -> List[Study]:
        """
        Fetch all studies from a Kheops album.

        Args:
            album_token: Token for album authentication

        Returns:
            List of Study objects

        Raises:
            KheopsAPIError: If API request fails
        """
        pass

    @abstractmethod
    def fetch_series(self, album_token: str, study_id: str) -> List[Series]:
        """
        Fetch all series within a study.

        Args:
            album_token: Token for album authentication
            study_id: ID of the study

        Returns:
            List of Series objects

        Raises:
            KheopsAPIError: If API request fails
        """
        pass

    @abstractmethod
    def fetch_instances(self, album_token: str, study_id: str, series_id: str) -> List[dict]:
        """
        Fetch all instances within a series.

        Args:
            album_token: Token for album authentication
            study_id: ID of the study
            series_id: ID of the series

        Returns:
            List of instance dictionaries with 'instance_id' and optional 'instance_url'

        Raises:
            KheopsAPIError: If API request fails
        """
        pass

    @abstractmethod
    def download_instance(self, album_token: str, study_id: str, series_id: str, instance_id: str, instance_url: str = None) -> bytes:
        """
        Download a DICOM instance as bytes.

        Args:
            album_token: Token for album authentication
            study_id: ID of the study
            series_id: ID of the series
            instance_id: ID of the DICOM instance
            instance_url: Optional URL from instance metadata (tag 00081190)

        Returns:
            DICOM file as bytes

        Raises:
            KheopsAPIError: If download fails
        """
        pass


class IDicomParser(ABC):
    """Interface for DICOM file parsing."""

    @abstractmethod
    def parse_dicom_file(self, dicom_bytes: bytes) -> DicomData:
        """
        Parse DICOM file bytes into DicomData object.

        Args:
            dicom_bytes: Raw DICOM file bytes

        Returns:
            Parsed DicomData object

        Raises:
            DicomParseError: If parsing fails
        """
        pass

    @abstractmethod
    def extract_pixel_array(self, dicom_data: DicomData) -> "np.ndarray":  # type: ignore
        """
        Extract pixel array from DICOM data.

        Args:
            dicom_data: Parsed DICOM data

        Returns:
            NumPy array of pixel data

        Raises:
            DicomParseError: If extraction fails
        """
        pass

    @abstractmethod
    def normalize_image(self, image: "np.ndarray") -> "np.ndarray":  # type: ignore
        """
        Normalize image array for model input.

        Args:
            image: Image array

        Returns:
            Normalized image array
        """
        pass


class IDiagnosisProvider(ABC):
    """Interface for diagnosis/abnormality detection following Interface Segregation Principle."""

    @abstractmethod
    def load_model(self, model_path: str) -> None:
        """
        Load MONAI model from file.

        Args:
            model_path: Path to model file

        Raises:
            ModelLoadError: If model loading fails
        """
        pass

    @abstractmethod
    def preprocess_image(self, image: "np.ndarray") -> "torch.Tensor":  # type: ignore
        """
        Preprocess image for model inference.

        Args:
            image: Image array

        Returns:
            Preprocessed tensor
        """
        pass

    @abstractmethod
    def run_inference(self, image_tensor: "torch.Tensor") -> DiagnosisResult:  # type: ignore
        """
        Run inference on preprocessed image.

        Args:
            image_tensor: Preprocessed image tensor

        Returns:
            DiagnosisResult with detected abnormalities
        """
        pass


class IReportGenerator(ABC):
    """Interface for LLM-based report generation."""

    @abstractmethod
    def initialize_llm(self, model_name: str) -> None:
        """
        Initialize LLM model.

        Args:
            model_name: Name of the LLM model

        Raises:
            LLMInitializationError: If initialization fails
        """
        pass

    @abstractmethod
    def create_prompt(self, diagnosis: DiagnosisResult) -> str:
        """
        Create prompt for LLM from diagnosis results.

        Args:
            diagnosis: Diagnosis results from MONAI

        Returns:
            Formatted prompt string
        """
        pass

    @abstractmethod
    def generate_report(self, prompt: str) -> str:
        """
        Generate clinical report from prompt.

        Args:
            prompt: Formatted prompt string

        Returns:
            Generated report text
        """
        pass

    @abstractmethod
    def format_report(self, raw_text: str) -> "ClinicalReport":  # type: ignore
        """
        Format raw LLM output into structured report.

        Args:
            raw_text: Raw LLM output

        Returns:
            Formatted ClinicalReport object
        """
        pass
