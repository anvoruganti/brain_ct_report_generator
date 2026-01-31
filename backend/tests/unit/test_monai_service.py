"""Unit tests for MONAI service."""

from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pytest
import torch

from backend.app.config import Settings
from backend.app.models.domain import DiagnosisResult
from backend.app.services.monai_service import MonaiService
from backend.app.utils.exceptions import ModelLoadError


class TestMonaiService:
    """Test MonaiService class."""

    def test_init_with_default_settings(self):
        """Test initialization with default settings."""
        # Arrange: No setup needed
        # Act: Create service instance
        service = MonaiService()

        # Assert: Verify settings and device
        assert service.settings is not None
        assert service.model is None

    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        # Arrange: Create custom settings
        custom_settings = Settings(monai_device="cpu")

        # Act: Create service with custom settings
        service = MonaiService(settings=custom_settings)

        # Assert: Verify custom settings are used
        assert service.settings == custom_settings

    @patch("backend.app.services.monai_service.torch.load")
    @patch("backend.app.services.monai_service.UNet")
    def test_load_model_success(self, mock_unet_class, mock_torch_load):
        """Test successful model loading."""
        # Arrange: Mock model and state dict
        mock_model = Mock()
        mock_model.load_state_dict = Mock()
        mock_model.to = Mock()
        mock_model.eval = Mock()
        mock_unet_class.return_value = mock_model
        mock_torch_load.return_value = {"layer1": torch.tensor([1.0])}

        service = MonaiService()
        model_path = "test_model.pth"

        # Act: Load model
        service.load_model(model_path)

        # Assert: Verify model is loaded
        assert service.model is not None
        mock_model.load_state_dict.assert_called_once()
        mock_model.to.assert_called_once()
        mock_model.eval.assert_called_once()

    @patch("backend.app.services.monai_service.torch.load")
    def test_load_model_failure(self, mock_torch_load):
        """Test model loading failure."""
        # Arrange: Mock load failure
        mock_torch_load.side_effect = Exception("File not found")

        service = MonaiService()
        model_path = "nonexistent.pth"

        # Act & Assert: Verify ModelLoadError is raised
        with pytest.raises(ModelLoadError):
            service.load_model(model_path)

    def test_preprocess_image_2d(self):
        """Test preprocessing 2D image."""
        # Arrange: Create 2D image
        image = np.random.rand(512, 512).astype(np.float32)
        service = MonaiService()

        # Act: Preprocess image
        tensor = service.preprocess_image(image)

        # Assert: Verify tensor shape
        assert isinstance(tensor, torch.Tensor)
        assert tensor.dim() == 4

    def test_preprocess_image_3d(self):
        """Test preprocessing 3D image."""
        # Arrange: Create 3D image
        image = np.random.rand(1, 512, 512).astype(np.float32)
        service = MonaiService()

        # Act: Preprocess image
        tensor = service.preprocess_image(image)

        # Assert: Verify tensor shape
        assert isinstance(tensor, torch.Tensor)
        assert tensor.dim() == 4

    def test_run_inference_without_model(self):
        """Test inference without loaded model."""
        # Arrange: Service without model
        service = MonaiService()
        image_tensor = torch.randn(1, 1, 256, 256)

        # Act & Assert: Verify ModelLoadError is raised
        with pytest.raises(ModelLoadError):
            service.run_inference(image_tensor)

    @patch("backend.app.services.monai_service.torch.load")
    @patch("backend.app.services.monai_service.UNet")
    def test_run_inference_success(self, mock_unet_class, mock_torch_load):
        """Test successful inference."""
        # Arrange: Mock model and output
        mock_model = Mock()
        mock_output = torch.randn(1, 2, 256, 256)
        mock_model.return_value = mock_output
        mock_model.eval = Mock()
        mock_unet_class.return_value = mock_model
        mock_torch_load.return_value = {"layer1": torch.tensor([1.0])}

        service = MonaiService()
        service.load_model("test_model.pth")
        service.model = mock_model

        image_tensor = torch.randn(1, 1, 256, 256)

        # Act: Run inference
        result = service.run_inference(image_tensor)

        # Assert: Verify DiagnosisResult
        assert isinstance(result, DiagnosisResult)
        assert "abnormalities" in result.abnormalities or "normal" in result.abnormalities
        assert "normal" in result.confidence_scores
        assert "abnormal" in result.confidence_scores

    def test_extract_abnormalities_normal(self):
        """Test abnormality extraction for normal case."""
        # Arrange: Create service and mock outputs
        service = MonaiService()
        predicted_class = torch.tensor([[0]])
        probabilities = torch.tensor([[[0.8, 0.2]]])

        # Act: Extract abnormalities
        abnormalities = service._extract_abnormalities(predicted_class, probabilities)

        # Assert: Verify normal result
        assert "normal" in abnormalities

    def test_extract_abnormalities_abnormal(self):
        """Test abnormality extraction for abnormal case."""
        # Arrange: Create service and mock outputs
        service = MonaiService()
        predicted_class = torch.tensor([[1]])
        probabilities = torch.tensor([[[0.3, 0.7]]])

        # Act: Extract abnormalities
        abnormalities = service._extract_abnormalities(predicted_class, probabilities)

        # Assert: Verify abnormal result
        assert "abnormal" in abnormalities

    def test_calculate_confidence_scores(self):
        """Test confidence score calculation."""
        # Arrange: Create service and probabilities
        service = MonaiService()
        probabilities = torch.tensor([[[0.6, 0.4]]])

        # Act: Calculate scores
        scores = service._calculate_confidence_scores(probabilities)

        # Assert: Verify scores
        assert "normal" in scores
        assert "abnormal" in scores
        assert isinstance(scores["normal"], float)
        assert isinstance(scores["abnormal"], float)
