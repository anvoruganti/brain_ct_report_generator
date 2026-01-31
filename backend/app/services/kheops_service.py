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

    def _parse_dicom_value(self, value: any) -> str | None:
        """
        Parse DICOM value which can be a string, list, or dict.

        Args:
            value: DICOM value (can be string, list, or dict)

        Returns:
            String value or None
        """
        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            if len(value) > 0:
                return self._parse_dicom_value(value[0])
            return None

        if isinstance(value, dict):
            if "Alphabetic" in value:
                return value["Alphabetic"]
            if "Value" in value:
                return self._parse_dicom_value(value["Value"])
            return str(value)

        return str(value) if value else None

    def _parse_patient_name(self, name_value: any) -> str | None:
        """
        Parse DICOM patient name which can be string or dict with components.

        Args:
            name_value: Patient name value from DICOM

        Returns:
            Patient name as string or None
        """
        if name_value is None:
            return None

        if isinstance(name_value, str):
            return name_value

        if isinstance(name_value, list) and len(name_value) > 0:
            name_value = name_value[0]

        if isinstance(name_value, dict):
            if "Alphabetic" in name_value:
                return name_value["Alphabetic"]
            if "Value" in name_value:
                return self._parse_patient_name(name_value["Value"])

        return str(name_value) if name_value else None

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
                study_id_tag = study_data.get("0020000D", {})
                study_date_tag = study_data.get("00080020", {})
                study_desc_tag = study_data.get("00081030", {})
                patient_id_tag = study_data.get("00100020", {})
                patient_name_tag = study_data.get("00100010", {})

                study_id_value = study_id_tag.get("Value", [""])
                study_date_value = study_date_tag.get("Value") if study_date_tag.get("Value") else None
                study_desc_value = study_desc_tag.get("Value") if study_desc_tag.get("Value") else None
                patient_id_value = patient_id_tag.get("Value") if patient_id_tag.get("Value") else None
                patient_name_value = patient_name_tag.get("Value") if patient_name_tag.get("Value") else None

                study = Study(
                    study_id=self._parse_dicom_value(study_id_value[0] if study_id_value else ""),
                    study_date=self._parse_dicom_value(study_date_value[0] if study_date_value else None),
                    study_description=self._parse_dicom_value(study_desc_value[0] if study_desc_value else None),
                    patient_id=self._parse_dicom_value(patient_id_value[0] if patient_id_value else None),
                    patient_name=self._parse_patient_name(patient_name_value),
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

    def fetch_instances(self, album_token: str, study_id: str, series_id: str) -> List[str]:
        """
        Fetch all instance IDs within a series.

        Args:
            album_token: Token for album authentication
            study_id: ID of the study
            series_id: ID of the series

        Returns:
            List of instance IDs

        Raises:
            KheopsAPIError: If API request fails
        """
        url = f"{self.base_url}/api/studies/{study_id}/series/{series_id}/instances"
        response = self._make_request("GET", url, album_token)

        try:
            instances_data = response.json()
            instance_ids = []

            for instance_item in instances_data:
                instance_id = instance_item.get("00080018", {}).get("Value", [""])[0]
                if instance_id:
                    instance_ids.append(instance_id)

            return instance_ids
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise KheopsAPIError(f"Failed to parse instances response: {str(e)}") from e

    def download_instance(self, album_token: str, study_id: str, series_id: str, instance_id: str) -> bytes:
        """
        Download a DICOM instance as bytes.

        Args:
            album_token: Token for album authentication
            study_id: ID of the study
            series_id: ID of the series
            instance_id: ID of the DICOM instance

        Returns:
            DICOM file as bytes

        Raises:
            KheopsAPIError: If download fails
        """
        url = f"{self.base_url}/api/studies/{study_id}/series/{series_id}/instances/{instance_id}/file"
        headers = self._get_headers(album_token)
        headers["Accept"] = "application/dicom"

        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise KheopsAPIError(f"Failed to download DICOM instance: {str(e)}") from e
