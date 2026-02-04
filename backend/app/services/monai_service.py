"""MONAI service for brain CT abnormality detection."""

import logging
from typing import Dict, Any, List, Optional, Union

import numpy as np

# Optional imports for MONAI - gracefully handle if not available (e.g., Python 3.13)
try:
    import torch
    from monai.networks.nets import UNet
    from monai.transforms import (
        Compose,
        EnsureChannelFirst,
        Resize,
        NormalizeIntensity,
        ToTensor,
        Transform,
    )
    MONAI_AVAILABLE = True
    TensorType = torch.Tensor
except ImportError:
    MONAI_AVAILABLE = False
    torch = None
    UNet = None
    Compose = None
    EnsureChannelFirst = None
    Resize = None
    NormalizeIntensity = None
    ToTensor = None
    Transform = None
    TensorType = Any  # Fallback type hint when torch is not available

from backend.app.config import Settings, get_settings
from backend.app.models.domain import DiagnosisResult
from backend.app.services.interfaces import IDiagnosisProvider
from backend.app.utils.exceptions import ModelLoadError

logger = logging.getLogger(__name__)


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
        
        if not MONAI_AVAILABLE:
            logger.warning(
                "MONAI/PyTorch not available (likely Python 3.13 compatibility issue). "
                "Using mock diagnosis mode for PoC."
            )
            self.device = None
            self.preprocess_transform = None
        else:
            # Auto-detect best device: MPS (M1 Mac) > CUDA > CPU
            device_setting = self.settings.monai_device.lower()
            if device_setting == "auto":
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self.device = torch.device("mps")
                    logger.info("✅ Using MPS (Metal) backend for M1 Mac acceleration")
                elif torch.cuda.is_available():
                    self.device = torch.device("cuda")
                    logger.info("✅ Using CUDA backend")
                else:
                    self.device = torch.device("cpu")
                    logger.info("Using CPU backend")
            elif device_setting == "mps":
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self.device = torch.device("mps")
                    logger.info("✅ Using MPS (Metal) backend")
                else:
                    logger.warning("MPS requested but not available, falling back to CPU")
                    self.device = torch.device("cpu")
            elif device_setting == "cuda":
                if torch.cuda.is_available():
                    self.device = torch.device("cuda")
                    logger.info("✅ Using CUDA backend")
                else:
                    logger.warning("CUDA requested but not available, falling back to CPU")
                    self.device = torch.device("cpu")
            else:
                self.device = torch.device("cpu")
                logger.info("Using CPU backend")
            self.preprocess_transform = self._create_preprocess_transform()

    def load_model(self, model_path: str) -> None:
        """
        Load MONAI model from file.

        Args:
            model_path: Path to model file

        Raises:
            ModelLoadError: If model loading fails or MONAI is not available
        """
        if not MONAI_AVAILABLE:
            raise ModelLoadError(
                "MONAI/PyTorch not available. Cannot load model. "
                "For Python 3.13, use Python 3.10-3.12 or wait for PyTorch 3.13 support."
            )
        
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

    def preprocess_image(self, image: np.ndarray):
        """
        Preprocess image for model inference.

        Args:
            image: Image array (2D or 3D)

        Returns:
            Preprocessed tensor (or None if MONAI not available)
        """
        if not MONAI_AVAILABLE or self.preprocess_transform is None:
            return None
        
        # Convert to float32 for MONAI transforms
        if image.dtype != np.float32:
            image = image.astype(np.float32)
        
        # If image already has channel dimension (3D with single channel), remove it first
        # EnsureChannelFirst expects 2D input and will add channel dimension
        if len(image.shape) == 3 and image.shape[0] == 1:
            # Remove the channel dimension if it's already there
            image = image.squeeze(0)
        
        # EnsureChannelFirst will handle adding channel dimension
        preprocessed = self.preprocess_transform(image)
        return preprocessed.unsqueeze(0).to(self.device)

    def run_inference(self, image_tensor: Optional[TensorType] = None) -> DiagnosisResult:
        """
        Run inference on preprocessed image.

        Args:
            image_tensor: Preprocessed image tensor (or None if MONAI not available)

        Returns:
            DiagnosisResult with detected abnormalities

        Raises:
            ModelLoadError: If model is not loaded (only in strict mode)
        """
        if not MONAI_AVAILABLE or self.model is None or image_tensor is None:
            # For PoC/testing: return mock diagnosis if model not loaded or MONAI unavailable
            logger.warning(
                "MONAI model not available or not loaded. Returning mock diagnosis for PoC/testing. "
                "To use real inference, provide a model file and ensure MONAI/PyTorch is installed."
            )
            return self._get_mock_diagnosis()

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
    
    def run_inference_batch(self, image_tensors: List[TensorType]) -> List[DiagnosisResult]:
        """
        Run inference on a batch of images (much faster than individual calls).
        
        This method processes multiple images in a single forward pass, which is
        significantly faster than calling run_inference() multiple times, especially
        on MPS/CUDA devices.

        Args:
            image_tensors: List of preprocessed image tensors

        Returns:
            List of DiagnosisResult objects (one per image)

        Raises:
            ModelLoadError: If model is not loaded
        """
        if not MONAI_AVAILABLE or self.model is None:
            return [self._get_mock_diagnosis() for _ in image_tensors]
        
        if not image_tensors:
            return []
        
        # Stack tensors into batch [batch_size, channels, height, width]
        batch = torch.stack(image_tensors).to(self.device)
        
        with torch.no_grad():
            output = self.model(batch)
            probabilities = torch.softmax(output, dim=1)
            predicted_classes = torch.argmax(probabilities, dim=1)
        
        # Process each image in batch
        results = []
        for i in range(len(image_tensors)):
            # Extract single image results from batch
            # predicted_classes shape: [batch, H, W], slice to [1, H, W]
            single_predicted = predicted_classes[i:i+1]
            # probabilities shape: [batch, 2, H, W], slice to [1, 2, H, W]
            single_probabilities = probabilities[i:i+1]
            
            abnormalities = self._extract_abnormalities(single_predicted, single_probabilities)
            confidence_scores = self._calculate_confidence_scores(single_probabilities)
            findings = self._extract_findings(output[i:i+1], single_probabilities)
            
            results.append(DiagnosisResult(
                abnormalities=abnormalities,
                confidence_scores=confidence_scores,
                findings=findings,
            ))
        
        return results

    def _get_mock_diagnosis(self) -> DiagnosisResult:
        """
        Generate mock diagnosis for PoC/testing when model is not available.

        Returns:
            Mock DiagnosisResult
        """
        from datetime import datetime
        return DiagnosisResult(
            abnormalities=["normal"],  # Default to normal for PoC
            confidence_scores={
                "normal": 0.85,
                "abnormal": 0.15,
            },
            findings={
                "mock_diagnosis": True,
                "note": "Mock diagnosis - model not loaded. Provide a MONAI model file for real inference.",
            },
            timestamp=datetime.now(),
        )

    def _create_preprocess_transform(self):
        """
        Create preprocessing transform pipeline.

        Returns:
            Composed transform (or None if MONAI not available)
        """
        if not MONAI_AVAILABLE:
            return None
        
        return Compose([
            EnsureChannelFirst(channel_dim="no_channel"),  # Explicitly specify no channel dimension exists
            Resize(spatial_size=(256, 256)),
            NormalizeIntensity(),
            ToTensor(),
        ])

    def _extract_abnormalities(self, predicted_class: TensorType, probabilities: TensorType) -> List[str]:
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

    def _calculate_confidence_scores(self, probabilities: TensorType) -> Dict[str, float]:
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

    def _extract_findings(self, output: TensorType, probabilities: TensorType) -> Dict[str, Any]:
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
