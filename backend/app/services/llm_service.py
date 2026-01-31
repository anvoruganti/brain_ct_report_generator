"""LLM service for generating clinical reports."""

import json
import re
from typing import Dict

import httpx

from backend.app.config import Settings, get_settings
from backend.app.models.domain import ClinicalReport, DiagnosisResult
from backend.app.services.interfaces import IReportGenerator
from backend.app.utils.exceptions import LLMInitializationError


class LLMService(IReportGenerator):
    """Service for LLM-based report generation using Ollama."""

    def __init__(self, settings: Settings = None):
        """
        Initialize LLM service.

        Args:
            settings: Application settings (defaults to get_settings())
        """
        self.settings = settings or get_settings()
        self.model_name = self.settings.llm_model_name
        self.base_url = self.settings.ollama_base_url
        self.initialized = False

    def initialize_llm(self, model_name: str = None) -> None:
        """
        Initialize LLM model.

        Args:
            model_name: Name of the LLM model (defaults to settings)

        Raises:
            LLMInitializationError: If initialization fails
        """
        try:
            model = model_name or self.model_name
            url = f"{self.base_url}/api/tags"

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                models = response.json().get("models", [])

                model_exists = any(m.get("name", "").startswith(model) for m in models)
                if not model_exists:
                    raise LLMInitializationError(f"Model {model} not found in Ollama")

            self.model_name = model
            self.initialized = True
        except Exception as e:
            raise LLMInitializationError(f"Failed to initialize LLM: {str(e)}") from e

    def create_prompt(self, diagnosis: DiagnosisResult) -> str:
        """
        Create prompt for LLM from diagnosis results.

        Args:
            diagnosis: Diagnosis results from MONAI

        Returns:
            Formatted prompt string
        """
        abnormalities_str = ", ".join(diagnosis.abnormalities) if diagnosis.abnormalities else "None detected"
        confidence_str = ", ".join([f"{k}: {v:.2f}" for k, v in diagnosis.confidence_scores.items()])

        prompt = f"""Based on the following CT scan analysis, generate a clinical report in the specified format.

CT Scan Analysis:
- Detected Abnormalities: {abnormalities_str}
- Confidence Scores: {confidence_str}
- Findings: {json.dumps(diagnosis.findings, indent=2)}

Please generate a clinical report in the following format:

Clinical History:
[Provide relevant clinical history if available]

Findings:
[Describe the findings from the CT scan analysis]

Impression:
[Provide clinical impression based on the findings]

Recommendations:
[Provide recommendations for follow-up or treatment]

Generate the report now:"""

        return prompt

    def generate_report(self, prompt: str) -> str:
        """
        Generate clinical report from prompt.

        Args:
            prompt: Formatted prompt string

        Returns:
            Generated report text
        """
        if not self.initialized:
            self.initialize_llm()

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            raise LLMInitializationError(f"Failed to generate report: {str(e)}") from e

    def format_report(self, raw_text: str) -> ClinicalReport:
        """
        Format raw LLM output into structured report.

        Args:
            raw_text: Raw LLM output

        Returns:
            Formatted ClinicalReport object
        """
        clinical_history = self._extract_section(raw_text, "Clinical History")
        findings = self._extract_section(raw_text, "Findings")
        impression = self._extract_section(raw_text, "Impression")
        recommendations = self._extract_section(raw_text, "Recommendations")

        return ClinicalReport(
            clinical_history=clinical_history,
            findings=findings,
            impression=impression,
            recommendations=recommendations,
        )

    def _extract_section(self, text: str, section_name: str) -> str | None:
        """
        Extract a section from the report text.

        Args:
            text: Full report text
            section_name: Name of the section to extract

        Returns:
            Section content or None if not found
        """
        pattern = rf"{section_name}:\s*(.*?)(?=\n\w+:|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if match:
            content = match.group(1).strip()
            return content if content else None

        return None
