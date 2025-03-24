"""
Mock implementations of services for testing.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image


class MockModelStorageService:
    """Mock implementation of ModelStorageService for testing."""

    def __init__(self):
        """Initialize the mock model storage service."""
        self.model_path = "/path/to/mock/model.tflite"

    def get_mobilenet_model_path(self):
        """Get a mock path to the MobileNet model."""
        return self.model_path


class MockTemplateService:
    """Mock implementation of TemplateManagementService for testing."""

    def __init__(self):
        """Initialize the mock template service."""
        self.templates = {
            "a": {"original": np.zeros((100, 100, 3), dtype=np.uint8)},
            "b": {"original": np.zeros((100, 100, 3), dtype=np.uint8)},
            "c": {"original": np.zeros((100, 100, 3), dtype=np.uint8)},
        }

    def get_template_list(self) -> List[str]:
        """Get a list of mock template names."""
        return list(self.templates.keys())

    def get_template_image(self, template_name: str) -> Optional[np.ndarray]:
        """Get a mock template image."""
        if template_name in self.templates:
            # Return a simple PIL Image
            return Image.new("RGB", (100, 100), color=(255, 255, 255))
        return None

    def load_all_templates(self) -> Dict[str, Dict[str, np.ndarray]]:
        """Load all mock templates."""
        return self.templates


class MockSVGService:
    """Mock implementation of SVGManagementService for testing."""

    def __init__(self):
        """Initialize the mock SVG service."""
        self.svg_content = {
            "a": '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="white"/><text x="50" y="50" text-anchor="middle">A</text></svg>',
            "b": '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="white"/><text x="50" y="50" text-anchor="middle">B</text></svg>',
            "c": '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="white"/><text x="50" y="50" text-anchor="middle">C</text></svg>',
        }

    def get_svg_list(self) -> List[str]:
        """Get a list of mock SVG names."""
        return list(self.svg_content.keys())

    def get_svg_content(self, svg_name: str) -> Optional[str]:
        """Get mock SVG content."""
        if svg_name in self.svg_content:
            return "<svg>Mock SVG Content</svg>"
        return None  # Return None for nonexistent SVGs

    def get_svg_url(self, svg_name: str) -> Optional[str]:
        """Get a mock URL for an SVG."""
        if svg_name in self.svg_content:
            return f"/media/sitelen_pona_svgs/{svg_name}.svg"
        return None


class MockCharacterRecognitionService:
    """Mock implementation of CharacterRecognitionService for testing."""

    def __init__(self):
        """Initialize the mock character recognition service."""
        self.initialized = True
        self.match_probability = 0.85  # Default confidence score
        self.all_scores = {
            "a": 0.85,
            "b": 0.65,
            "c": 0.45,
        }

    def initialize(self):
        """Initialize the mock service."""
        self.initialized = True

    def recognize(self, drawn_image, threshold=0.7) -> Tuple[Optional[str], float]:
        """Mock character recognition."""
        # Always return 'a' with the configured confidence
        if self.match_probability >= threshold:
            return "a", self.match_probability
        return None, self.match_probability

    def recognize_base64(
        self, base64_image: str, threshold=0.7
    ) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """Mock base64 image recognition."""
        # Generate deterministic but random-seeming result based on the image hash
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]

        # Use a hash of the first 100 chars of the base64 string to determine the character
        hash_val = sum(ord(c) for c in base64_image[:100]) % 100

        # Use the hash to determine a "match"
        if hash_val < 70:  # 70% chance of matching 'a'
            char_name = "a"
            match_score = 0.8 + (hash_val % 20) / 100  # Score between 0.8 and 0.99
        else:
            # Return a different character
            others = ["b", "c"]
            char_name = others[hash_val % 2]
            match_score = 0.5 + (hash_val % 30) / 100  # Score between 0.5 and 0.79

        # Create all_scores with the match as highest
        all_scores = {
            "a": 0.5,
            "b": 0.4,
            "c": 0.3,
        }
        all_scores[char_name] = match_score

        # Return results
        if match_score >= threshold:
            return char_name, match_score, {"scores": all_scores}
        return None, match_score, {"scores": all_scores}

    def set_match_probability(self, probability: float):
        """Set the match probability for testing different scenarios."""
        self.match_probability = probability
