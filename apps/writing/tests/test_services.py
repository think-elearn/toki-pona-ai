"""
Tests for Writing app service classes.
"""

import base64
import io
import os
from unittest.mock import patch

import numpy as np
from django.conf import settings
from django.test import TestCase
from PIL import Image

from apps.writing.services.ml_storage import ModelStorageService
from apps.writing.services.recognition import CharacterRecognitionService
from apps.writing.tests.mocks import (
    MockCharacterRecognitionService,
    MockModelStorageService,
    MockSVGService,
    MockTemplateService,
)


class ModelStorageServiceTests(TestCase):
    """Tests for the ModelStorageService class."""

    def setUp(self):
        """Set up test environment."""
        # Ensure test_ml_models directory exists
        os.makedirs(settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"], exist_ok=True)

    @patch("apps.writing.services.ml_storage.cache")
    def test_get_mobilenet_model_path_cached(self, mock_cache):
        """Test that cached model path is returned if available."""
        # Configure mock cache to return a cached path
        mock_path = os.path.join(
            settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"], "test_model.tflite"
        )
        mock_cache.get.return_value = mock_path

        # Create a file at the mock path to satisfy the os.path.exists check
        with open(mock_path, "w") as f:
            f.write("Mock model content")

        service = ModelStorageService()
        result = service.get_mobilenet_model_path()

        # Verify the expected path is returned
        self.assertEqual(result, mock_path)
        mock_cache.get.assert_called_once_with(service.MOBILENET_CACHE_KEY)

        # Clean up test file
        os.remove(mock_path)

    @patch("apps.writing.services.ml_storage.cache")
    @patch("apps.writing.services.ml_storage.os.path.exists")
    @patch("apps.writing.services.ml_storage.ModelStorageService._download_model")
    def test_get_mobilenet_local_not_cached(
        self, mock_download, mock_exists, mock_cache
    ):
        """Test model download when not in cache and using local storage."""
        # Configure cache to indicate no cached path
        mock_cache.get.return_value = None

        # Configure os.path.exists to return False first (file doesn't exist)
        mock_exists.return_value = False

        # Configure the download mock
        local_path = os.path.join(
            settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"],
            settings.ML_MODELS_STORAGE["MOBILENET_MODEL_PATH"],
        )

        # Create service and call method
        service = ModelStorageService()
        result = service.get_mobilenet_model_path()

        # Verify download is called with correct parameters
        mock_download.assert_called_once_with(
            settings.ML_MODELS_STORAGE["MOBILENET_MODEL_URL"], local_path
        )

        # Verify cache is updated
        mock_cache.set.assert_called_once_with(
            service.MOBILENET_CACHE_KEY, local_path, timeout=3600
        )

        # Verify correct path is returned
        self.assertEqual(result, local_path)


class CharacterRecognitionServiceTests(TestCase):
    """Tests for the CharacterRecognitionService class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_service = MockCharacterRecognitionService()

    @patch("apps.writing.services.recognition.model_storage", MockModelStorageService())
    @patch("apps.writing.services.recognition.MEDIAPIPE_AVAILABLE", False)
    def test_initialize_mediapipe_not_available(self):
        """Test initialization when MediaPipe is not available."""
        service = CharacterRecognitionService()
        service.initialize()

        # Verify the service is not initialized since MediaPipe is not available
        self.assertFalse(service.initialized)

    def test_recognize_returns_expected_result(self):
        """Test that recognize method returns expected results."""
        # Create a simple test image
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        # Get recognition result with default threshold
        character, confidence = self.mock_service.recognize(test_image)

        # Verify expected results
        self.assertEqual(character, "a")
        self.assertEqual(confidence, self.mock_service.match_probability)

    def test_recognize_respects_threshold(self):
        """Test that recognize method respects the confidence threshold."""
        # Create a simple test image
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        # Set confidence below threshold
        self.mock_service.set_match_probability(0.5)

        # Get recognition result with higher threshold
        character, confidence = self.mock_service.recognize(test_image, threshold=0.8)

        # Verify no match due to low confidence
        self.assertIsNone(character)
        self.assertEqual(confidence, 0.5)

    def test_recognize_base64(self):
        """Test recognition from base64 image data."""
        # Create a simple image and convert to base64
        image = Image.new("RGB", (100, 100), color=(255, 255, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        base64_image = (
            "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        )

        # Get recognition result
        character, confidence, debug_info = self.mock_service.recognize_base64(
            base64_image
        )

        # Verify proper results
        self.assertIsNotNone(character)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        self.assertIn("scores", debug_info)


class SVGManagementServiceTests(TestCase):
    """Tests for the SVGManagementService class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_service = MockSVGService()

    def test_get_svg_list(self):
        """Test getting a list of available SVGs."""
        svg_list = self.mock_service.get_svg_list()

        # Verify expected SVG list
        self.assertEqual(len(svg_list), 3)
        self.assertIn("a", svg_list)
        self.assertIn("b", svg_list)
        self.assertIn("c", svg_list)

    def test_get_svg_content_existing(self):
        """Test getting content for an existing SVG."""
        svg_content = self.mock_service.get_svg_content("a")

        # Verify correct SVG content
        self.assertIsNotNone(svg_content)
        self.assertIn("<svg", svg_content)

    def test_get_svg_content_nonexistent(self):
        """Test getting content for a non-existent SVG."""
        svg_content = self.mock_service.get_svg_content("nonexistent")

        # Verify None is returned
        self.assertIsNone(svg_content)

    def test_get_svg_url(self):
        """Test getting URL for an SVG."""
        svg_url = self.mock_service.get_svg_url("a")

        # Verify expected URL format
        self.assertIsNotNone(svg_url)
        self.assertTrue(svg_url.startswith("/media/sitelen_pona_svgs/"))
        self.assertTrue(svg_url.endswith(".svg"))


class TemplateManagementServiceTests(TestCase):
    """Tests for the TemplateManagementService class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_service = MockTemplateService()

    def test_get_template_list(self):
        """Test getting a list of available templates."""
        template_list = self.mock_service.get_template_list()

        # Verify expected template list
        self.assertEqual(len(template_list), 3)
        self.assertIn("a", template_list)
        self.assertIn("b", template_list)
        self.assertIn("c", template_list)

    def test_get_template_image(self):
        """Test getting a template image."""
        template_image = self.mock_service.get_template_image("a")

        # Verify image is returned
        self.assertIsNotNone(template_image)

        # Verify it's a PIL Image object
        self.assertIsInstance(template_image, Image.Image)

        # Verify image dimensions
        self.assertEqual(template_image.width, 100)
        self.assertEqual(template_image.height, 100)

    def test_load_all_templates(self):
        """Test loading all templates."""
        templates = self.mock_service.load_all_templates()

        # Verify expected templates structure
        self.assertEqual(len(templates), 3)
        self.assertIn("a", templates)
        self.assertIn("b", templates)
        self.assertIn("c", templates)

        # Verify template content
        for template_data in templates.values():
            self.assertIn("original", template_data)
            self.assertIsNotNone(template_data["original"])
