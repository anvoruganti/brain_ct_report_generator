"""Kheops service for fetching DICOM data using album tokens."""

import json
from typing import List

import requests

from backend.app.config import Settings, get_settings
from backend.app.models.domain import Series, Study
from backend.app.services.interfaces import IKheopsClient
from backend.app.utils.exceptions import KheopsAPIError


class KheopsService(IKheopsClient):
    """Service for interacting with Kheops DICOMweb API."""

    def __init__(self, settings: Settings = None):
        """
        Initialize Kheops service.

        Args:
            settings: Application settings (defaults to get_settings())
        """
        self.settings = settings or get_settings()
        self.base_url = self.settings.kheops_base_url.rstrip("/")

    def _get_headers(self, album_token: str) -> dict:
        """
        Get HTTP headers for Kheops API requests.

        Args:
            album_token: Album token for authentication

        Returns:
            Dictionary with headers
        """
        return {
            "Authorization": f"Bearer {album_token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, url: str, album_token: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to Kheops API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL for the request
            album_token: Album token for authentication
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            KheopsAPIError: If request fails
        """
        headers = self._get_headers(album_token)
        headers.update(kwargs.pop("headers", {}))

        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise KheopsAPIError(f"Kheops API request failed: {str(e)}") from e

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
        url = f"{self.base_url}/api/studies"
        response = self._make_request("GET", url, album_token)

        try:
            studies_data = response.json()
            studies = []

            for study_data in studies_data:
                study = Study(
                    study_id=study_data.get("0020000D", {}).get("Value", [""])[0],
                    study_date=study_data.get("00080020", {}).get("Value", [""])[0] if study_data.get("00080020") else None,
                    study_description=study_data.get("00081030", {}).get("Value", [""])[0] if study_data.get("00081030") else None,
                    patient_id=study_data.get("00100020", {}).get("Value", [""])[0] if study_data.get("00100020") else None,
                    patient_name=study_data.get("00100010", {}).get("Value", [""])[0] if study_data.get("00100010") else None,
                )
                studies.append(study)

            return studies
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise KheopsAPIError(f"Failed to parse studies response: {str(e)}") from e

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
        url = f"{self.base_url}/api/studies/{study_id}/series"
        response = self._make_request("GET", url, album_token)

        try:
            series_data = response.json()
            series_list = []

            for series_item in series_data:
                series = Series(
                    series_id=series_item.get("0020000E", {}).get("Value", [""])[0],
                    study_id=study_id,
                    series_description=series_item.get("0008103E", {}).get("Value", [""])[0] if series_item.get("0008103E") else None,
                    modality=series_item.get("00080060", {}).get("Value", [""])[0] if series_item.get("00080060") else None,
                    instance_count=len(series_item.get("00081190", {}).get("Value", [])) if series_item.get("00081190") else None,
                )
                series_list.append(series)

            return series_list
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise KheopsAPIError(f"Failed to parse series response: {str(e)}") from e

    def download_instance(self, album_token: str, instance_id: str) -> bytes:
        """
        Download a DICOM instance as bytes.

        Args:
            album_token: Token for album authentication
            instance_id: ID of the DICOM instance

        Returns:
            DICOM file as bytes

        Raises:
            KheopsAPIError: If download fails
        """
        url = f"{self.base_url}/api/instances/{instance_id}/file"
        headers = self._get_headers(album_token)
        headers["Accept"] = "application/dicom"

        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise KheopsAPIError(f"Failed to download DICOM instance: {str(e)}") from e
