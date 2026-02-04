"""LLM service for generating clinical reports."""

import json
import logging
import re
from typing import Dict, List

import httpx

from backend.app.config import Settings, get_settings
from backend.app.models.domain import ClinicalReport, DiagnosisResult
from backend.app.services.interfaces import IReportGenerator
from backend.app.utils.exceptions import LLMInitializationError

logger = logging.getLogger(__name__)


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
        self._use_mock = False  # Flag to use mock reports when Ollama unavailable

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
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, ConnectionRefusedError) as e:
            # For PoC: Don't fail if Ollama is not running or times out, use mock mode instead
            logger.warning(
                f"Ollama not available or timed out at {self.base_url}. Using mock report generation for PoC. "
                "To use real LLM reports, ensure Ollama is running and responsive."
            )
            self.initialized = False  # Mark as not initialized, will use mock
            self._use_mock = True
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
        # #region agent log
        import json
        import time
        try:
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:70","message":"create_prompt entry","data":{"has_abnormalities":hasattr(diagnosis,'abnormalities'),"abnormalities_count":len(diagnosis.abnormalities) if hasattr(diagnosis,'abnormalities') else 0},"timestamp":int(time.time()*1000)})+'\n')
        except:
            pass
        # #endregion
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

        # #region agent log
        try:
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:115","message":"create_prompt exit","data":{"prompt_length":len(prompt)},"timestamp":int(time.time()*1000)})+'\n')
        except:
            pass
        # #endregion
        return prompt

    def generate_report(self, prompt: str) -> str:
        """
        Generate clinical report from prompt.

        Args:
            prompt: Formatted prompt string

        Returns:
            Generated report text
        """
        # #region agent log
        import json
        import time
        with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:117","message":"generate_report entry","data":{"initialized":self.initialized,"use_mock":self._use_mock,"base_url":self.base_url,"model_name":self.model_name},"timestamp":int(time.time()*1000)})+'\n')
        # #endregion
        
        # Try to initialize if not already done
        if not self.initialized and not self._use_mock:
            try:
                self.initialize_llm()
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, ConnectionRefusedError):
                # Connection failed or timeout, use mock mode
                self._use_mock = True
                logger.warning("Ollama connection/timeout failed. Using mock report generation for PoC.")
        
        # Use mock report if Ollama is unavailable
        if self._use_mock or not self.initialized:
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:144","message":"Using mock report","data":{},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            return self._generate_mock_report(prompt)

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }

        try:
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:151","message":"Before HTTP request","data":{"url":url},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            timeout = self.settings.llm_timeout
            with httpx.Client(timeout=float(timeout)) as client:
                response = client.post(url, json=payload)
                # #region agent log
                with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:164","message":"After HTTP request","data":{"status_code":response.status_code},"timestamp":int(time.time()*1000)})+'\n')
                # #endregion
                response.raise_for_status()
                result = response.json()
                # #region agent log
                with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:170","message":"After parse response","data":{"has_response":"response" in result},"timestamp":int(time.time()*1000)})+'\n')
                # #endregion
                return result.get("response", "")
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, ConnectionRefusedError) as e:
            # Connection failed or timeout, fallback to mock
            logger.warning(f"Ollama connection/timeout failed during generation: {e}. Using mock report.")
            self._use_mock = True
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:183","message":"Connection/timeout error, using mock","data":{"error_type":type(e).__name__},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            return self._generate_mock_report(prompt)
        except Exception as e:
            # #region agent log
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:193","message":"LLM generate_report exception","data":{"error_type":type(e).__name__,"error_msg":str(e)},"timestamp":int(time.time()*1000)})+'\n')
            # #endregion
            raise LLMInitializationError(f"Failed to generate report: {str(e)}") from e

    def _generate_mock_report(self, prompt: str) -> str:
        """
        Generate mock clinical report for PoC when Ollama is unavailable.

        Args:
            prompt: Formatted prompt string (used to extract diagnosis info)

        Returns:
            Mock report text
        """
        # Extract diagnosis info from prompt if possible
        abnormalities = "normal"
        if "Abnormalities:" in prompt:
            try:
                abn_line = [l for l in prompt.split('\n') if 'Abnormalities:' in l][0]
                abnormalities = abn_line.split('Abnormalities:')[1].strip()
            except:
                pass

        mock_report = f"""Clinical History:
No specific clinical history provided. Patient presented for routine CT brain imaging.

Findings:
CT brain scan analysis indicates {abnormalities.lower()} findings. The scan demonstrates normal brain parenchyma with no acute intracranial abnormalities detected. Ventricular system appears normal in size and configuration. No evidence of mass effect, hemorrhage, or acute infarction.

Impression:
Normal brain CT scan. No acute intracranial pathology identified.

Recommendations:
Routine follow-up as clinically indicated. If symptoms persist, consider clinical correlation and follow-up imaging if warranted.

Note: This is a mock report generated for PoC testing. For real LLM-generated reports, ensure Ollama is running and the model '{self.model_name}' is available."""
        
        return mock_report

    def format_report(self, raw_text: str) -> ClinicalReport:
        """
        Format raw LLM output into structured report.

        Args:
            raw_text: Raw LLM output

        Returns:
            Formatted ClinicalReport object
        """
        # #region agent log
        import json
        import time
        try:
            with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:234","message":"format_report entry","data":{"raw_text_length":len(raw_text) if raw_text else 0},"timestamp":int(time.time()*1000)})+'\n')
        except:
            pass
        # #endregion
        try:
            clinical_history = self._extract_section(raw_text, "Clinical History")
            findings = self._extract_section(raw_text, "Findings")
            impression = self._extract_section(raw_text, "Impression")
            recommendations = self._extract_section(raw_text, "Recommendations")

            report = ClinicalReport(
                clinical_history=clinical_history,
                findings=findings,
                impression=impression,
                recommendations=recommendations,
            )
            # #region agent log
            try:
                with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:254","message":"format_report exit","data":{"has_findings":hasattr(report,'findings'),"has_impression":hasattr(report,'impression')},"timestamp":int(time.time()*1000)})+'\n')
            except:
                pass
            # #endregion
            return report
        except Exception as e:
            # #region agent log
            try:
                with open('/Users/anirudh/Desktop/workspace/CT Brain Image Software/brain_ct_report_generator/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"llm_service.py:257","message":"format_report exception","data":{"error_type":type(e).__name__,"error_msg":str(e)},"timestamp":int(time.time()*1000)})+'\n')
            except:
                pass
            # #endregion
            raise

    def create_chunk_summary_prompt(self, chunk_diagnosis: DiagnosisResult, chunk_index: int, total_chunks: int, previous_summaries: List[str] = None) -> str:
        """
        Create a prompt for summarizing a chunk of diagnoses.
        
        Args:
            chunk_diagnosis: Aggregated diagnosis for this chunk
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
            previous_summaries: List of summaries from previous chunks
            
        Returns:
            Formatted prompt string for chunk summarization
        """
        abnormalities_str = ", ".join(chunk_diagnosis.abnormalities) if chunk_diagnosis.abnormalities else "None detected"
        confidence_str = ", ".join([f"{k}: {v:.2f}" for k, v in chunk_diagnosis.confidence_scores.items()])
        
        context_note = ""
        if previous_summaries:
            context_note = f"\n\nPrevious Chunks Summary:\n" + "\n\n".join([
                f"Chunk {i+1} Summary:\n{summary}" 
                for i, summary in enumerate(previous_summaries)
            ])
        
        prompt = f"""You are analyzing Chunk {chunk_index + 1} of {total_chunks} from a CT brain scan series.

Chunk {chunk_index + 1} Analysis:
- Detected Abnormalities: {abnormalities_str}
- Confidence Scores: {confidence_str}
- Number of Images: {chunk_diagnosis.findings.get('total_images_analyzed', 'N/A')}
- Findings: {json.dumps(chunk_diagnosis.findings, indent=2)}
{context_note}

Generate a concise summary (2-3 sentences) focusing on:
1. Key abnormalities or normal findings
2. Notable patterns or observations
3. Any critical findings that need attention

Summary:"""
        
        return prompt
    
    def create_final_report_prompt(self, chunk_summaries: List[str], final_diagnosis: DiagnosisResult) -> str:
        """
        Create a prompt for generating the final comprehensive report from chunk summaries.
        
        Args:
            chunk_summaries: List of summaries from all chunks
            final_diagnosis: Final aggregated diagnosis
            
        Returns:
            Formatted prompt string for final report generation
        """
        abnormalities_str = ", ".join(final_diagnosis.abnormalities) if final_diagnosis.abnormalities else "None detected"
        confidence_str = ", ".join([f"{k}: {v:.2f}" for k, v in final_diagnosis.confidence_scores.items()])
        
        summaries_text = "\n\n".join([
            f"Chunk {i+1} Summary:\n{summary}" 
            for i, summary in enumerate(chunk_summaries)
        ])
        
        prompt = f"""Based on the analysis of a complete CT brain scan series, generate a comprehensive clinical report.

The series was analyzed in {len(chunk_summaries)} chunks. Here are the summaries from each chunk:

{summaries_text}

Final Aggregated Analysis:
- Detected Abnormalities: {abnormalities_str}
- Confidence Scores: {confidence_str}
- Total Images Analyzed: {final_diagnosis.findings.get('total_images_analyzed', 'N/A')}
- Detailed Findings: {json.dumps(final_diagnosis.findings, indent=2)}

Please generate a comprehensive clinical report in the following format:

Clinical History:
[Provide relevant clinical history if available]

Findings:
[Describe the findings from the CT scan analysis across all chunks, integrating information from the chunk summaries]

Impression:
[Provide clinical impression based on the comprehensive findings]

Recommendations:
[Provide recommendations for follow-up or treatment]

Generate the comprehensive report now:"""
        
        return prompt

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
