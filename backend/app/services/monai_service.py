"""MONAI service for brain CT abnormality detection."""

from typing import Dict, Any, List

import numpy as np
import torch
from monai.networks.nets import UNet
from monai.transforms import (
    Compose,
    EnsureChannelFirst,
    Resize,
    NormalizeIntensity,
    ToTensor,
)

from backend.app.config import Settings, get_settings
from backend.app.models.domain import DiagnosisResult
from backend.app.services.interfaces import IDiagnosisProvider
from backend.app.utils.exceptions import ModelLoadError


class MonaiService(IDiagnosisProvider):
    """Service for MONAI model inference."""

    def __init__(self, settings: Settings = None):
        """
        Initialize MONAI service.

        Args:
            settings: Application settings (defaults to get_settings())
        """
        self.settings = settings or get_settings()
        self.model = None
        self.device = torch.device(self.settings.monai_device if torch.cuda.is_available() else "cpu")
        self.preprocess_transform = self._create_preprocess_transform()

    def load_model(self, model_path: str) -> None:
        """
        Load MONAI model from file.

        Args:
            model_path: Path to model file

        Raises:
            ModelLoadError: If model loading fails
        """
        try:
            model = UNet(
                spatial_dims=2,
                in_channels=1,
                out_channels=2,
                channels=(16, 32, 64, 128, 256),
                strides=(2, 2, 2, 2),
                num_res_units=2,
            )
            model.load_state_dict(torch.load(model_path, map_location=self.device))
            model.to(self.device)
            model.eval()
            self.model = model
        except Exception as e:
            raise ModelLoadError(f"Failed to load MONAI model: {str(e)}") from e

    def preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model inference.

        Args:
            image: Image array

        Returns:
            Preprocessed tensor
        """
        if len(image.shape) == 2:
            image = np.expand_dims(image, axis=0)

        image_dict = {"image": image}
        preprocessed = self.preprocess_transform(image_dict)
        return preprocessed["image"].unsqueeze(0).to(self.device)

    def run_inference(self, image_tensor: torch.Tensor) -> DiagnosisResult:
        """
        Run inference on preprocessed image.

        Args:
            image_tensor: Preprocessed image tensor

        Returns:
            DiagnosisResult with detected abnormalities
        """
        if self.model is None:
            raise ModelLoadError("Model not loaded. Call load_model() first.")

        with torch.no_grad():
            output = self.model(image_tensor)
            probabilities = torch.softmax(output, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1)

        abnormalities = self._extract_abnormalities(predicted_class, probabilities)
        confidence_scores = self._calculate_confidence_scores(probabilities)
        findings = self._extract_findings(output, probabilities)

        return DiagnosisResult(
            abnormalities=abnormalities,
            confidence_scores=confidence_scores,
            findings=findings,
        )

    def _create_preprocess_transform(self) -> Compose:
        """
        Create preprocessing transform pipeline.

        Returns:
            Composed transform
        """
        return Compose([
            EnsureChannelFirst(keys="image"),
            Resize(spatial_size=(256, 256), keys="image"),
            NormalizeIntensity(keys="image"),
            ToTensor(keys="image"),
        ])

    def _extract_abnormalities(self, predicted_class: torch.Tensor, probabilities: torch.Tensor) -> List[str]:
        """
        Extract detected abnormalities from model output.

        Args:
            predicted_class: Predicted class tensor
            probabilities: Probability tensor

        Returns:
            List of abnormality names
        """
        abnormalities = []
        class_names = ["normal", "abnormal"]

        unique_classes = torch.unique(predicted_class)
        for class_idx in unique_classes:
            if class_idx.item() == 1:
                max_prob = torch.max(probabilities[0, 1]).item()
                if max_prob > 0.5:
                    abnormalities.append(class_names[1])

        return abnormalities if abnormalities else ["normal"]

    def _calculate_confidence_scores(self, probabilities: torch.Tensor) -> Dict[str, float]:
        """
        Calculate confidence scores for each class.

        Args:
            probabilities: Probability tensor

        Returns:
            Dictionary with confidence scores
        """
        return {
            "normal": torch.mean(probabilities[0, 0]).item(),
            "abnormal": torch.mean(probabilities[0, 1]).item(),
        }

    def _extract_findings(self, output: torch.Tensor, probabilities: torch.Tensor) -> Dict[str, Any]:
        """
        Extract detailed findings from model output.

        Args:
            output: Raw model output
            probabilities: Probability tensor

        Returns:
            Dictionary with findings
        """
        return {
            "max_probability": torch.max(probabilities).item(),
            "mean_probability": torch.mean(probabilities).item(),
            "output_shape": list(output.shape),
        }
