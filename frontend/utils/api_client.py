"""FastAPI client wrapper for Streamlit frontend."""

from typing import Dict, List, Optional

import requests


class APIClient:
    """Client for interacting with FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize API client.

        Args:
            base_url: Base URL of the FastAPI backend
        """
        self.base_url = base_url.rstrip("/")

    def health_check(self) -> Dict:
        """
        Check API health.

        Returns:
            Health status dictionary

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        response = requests.get(f"{self.base_url}/api/health", timeout=5)
        response.raise_for_status()
        return response.json()

    def get_studies(self, album_token: str) -> List[Dict]:
        """
        Get studies from Kheops album.

        Args:
            album_token: Album token for authentication

        Returns:
            List of study dictionaries

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        response = requests.get(
            f"{self.base_url}/api/kheops/studies",
            params={"album_token": album_token},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["studies"]

    def get_series(self, study_id: str, album_token: str) -> List[Dict]:
        """
        Get series within a study.

        Args:
            study_id: Study instance UID
            album_token: Album token for authentication

        Returns:
            List of series dictionaries

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        response = requests.get(
            f"{self.base_url}/api/kheops/studies/{study_id}/series",
            params={"album_token": album_token},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["series"]

    def generate_report_from_kheops(
        self, album_token: str, study_id: str, series_id: Optional[str] = None
    ) -> Dict:
        """
        Generate report from Kheops study.

        Args:
            album_token: Album token for authentication
            study_id: Study instance UID
            series_id: Optional series instance UID

        Returns:
            Report dictionary

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        payload = {"album_token": album_token, "study_id": study_id}
        if series_id:
            payload["series_id"] = series_id

        response = requests.post(
            f"{self.base_url}/api/inference/from-kheops",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def generate_report_from_dicom(self, dicom_file: bytes, filename: str = "upload.dcm") -> Dict:
        """
        Generate report from uploaded DICOM file.

        Args:
            dicom_file: DICOM file bytes
            filename: Filename for upload

        Returns:
            Report dictionary

        Raises:
            RuntimeError: If request fails, with detailed backend error information
        """
        import json
        
        files = [("dicom_files", (filename, dicom_file, "application/dicom"))]
        response = requests.post(
            f"{self.base_url}/api/inference/from-dicom",
            files=files,
            timeout=300,  # Increased timeout for multiple files
        )
        
        if not response.ok:
            try:
                detail = response.json()
            except Exception:
                detail = {"raw_text": response.text[:4000]}
            
            error_msg = f"Backend error {response.status_code}:\n{json.dumps(detail, indent=2)}"
            raise RuntimeError(error_msg)
        
        return response.json()

    def generate_report_from_dicom_series(self, dicom_files: List[bytes], filenames: List[str]) -> Dict:
        """
        Generate report from multiple uploaded DICOM files (series).

        Args:
            dicom_files: List of DICOM file bytes
            filenames: List of filenames for upload

        Returns:
            Report dictionary

        Raises:
            RuntimeError: If request fails, with detailed backend error information
        """
        import json
        
        files = [
            ("dicom_files", (filename, dicom_bytes, "application/dicom"))
            for dicom_bytes, filename in zip(dicom_files, filenames)
        ]
        response = requests.post(
            f"{self.base_url}/api/inference/from-dicom",
            files=files,
            timeout=600,  # Longer timeout for multiple files
        )
        
        if not response.ok:
            try:
                detail = response.json()
            except Exception:
                detail = {"raw_text": response.text[:4000]}
            
            error_msg = f"Backend error {response.status_code}:\n{json.dumps(detail, indent=2)}"
            raise RuntimeError(error_msg)
        
        return response.json()
