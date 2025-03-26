"""
Pytest fixtures for writing app tests.
"""

import os
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.files.base import ContentFile

from apps.writing.models import Glyph


@pytest.fixture
def temp_model_dir(monkeypatch, tmp_path):
    """Create temporary model directory for testing."""
    original_dir = settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"]
    original_media_root = getattr(settings, "MEDIA_ROOT", None)

    # Create media subdirectory in the temp path
    ml_models_dir = tmp_path / "ml_models"
    ml_models_dir.mkdir(exist_ok=True)

    # Set MEDIA_ROOT to the temp_path
    settings.MEDIA_ROOT = str(tmp_path)

    # Since ML_MODELS_STORAGE is a dict, we need to modify it directly
    settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"] = str(ml_models_dir)

    yield tmp_path

    # Restore original settings
    settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"] = original_dir
    if original_media_root is not None:
        settings.MEDIA_ROOT = original_media_root


@pytest.fixture
def mock_download():
    """Mock model download to prevent actual downloads."""
    with patch("apps.writing.services.ml_storage.urllib.request.urlretrieve") as mock:
        # Create a side effect that touches the file to simulate download
        def touch_file(*args):
            _, dest_path = args
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "w") as f:
                f.write("Mock model content")
            return dest_path, None

        mock.side_effect = touch_file
        yield mock


@pytest.fixture
def is_ci_environment():
    """Check if running in CI environment."""
    return os.environ.get("CI") == "true"


@pytest.fixture
def test_static_svgs(tmp_path):
    """Create test SVG files in the static directory for testing."""
    # Create a temporary static/images/glyphs directory
    test_static_dir = tmp_path / "static" / "images" / "glyphs"
    test_static_dir.mkdir(parents=True, exist_ok=True)

    # Define a simple test SVG content
    svg_content = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="none" />
  <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="none" />
</svg>"""

    # Create test SVG files
    test_glyphs = ["toki", "pona", "mi"]
    for glyph_name in test_glyphs:
        svg_path = test_static_dir / f"{glyph_name}.svg"
        with open(svg_path, "w") as f:
            f.write(svg_content)

    # Patch settings.BASE_DIR temporarily to point to our test directory
    original_base_dir = settings.BASE_DIR
    settings.BASE_DIR = tmp_path

    yield test_glyphs

    # Restore original settings
    settings.BASE_DIR = original_base_dir


@pytest.fixture
def glyph_with_images(tmp_path):
    """Create a Glyph instance with test images."""
    # Create test directories
    media_root = tmp_path / "media"
    media_root.mkdir(parents=True, exist_ok=True)

    # Create a test glyph
    glyph = Glyph.objects.create(
        name="test_glyph",
        meaning="Test glyph",
        difficulty=Glyph.DifficultyLevel.BEGINNER,
        category=Glyph.Category.BASIC,
    )

    # Add test image content
    test_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00:~\x9bU\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    test_svg = b'<svg width="1" height="1"></svg>'

    # Add images to glyph
    glyph.image.save("test_glyph.png", ContentFile(test_png), save=False)
    glyph.reference_image.save("test_glyph.svg", ContentFile(test_svg), save=True)

    return glyph
