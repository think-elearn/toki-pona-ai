"""
Pytest fixtures for writing app tests.
"""

import os
from unittest.mock import patch

import pytest
from django.conf import settings


@pytest.fixture
def temp_model_dir(monkeypatch, tmp_path):
    """Create temporary model directory for testing."""
    original_dir = settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"]
    # Since ML_MODELS_STORAGE is a dict, we need to modify it directly
    settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"] = str(tmp_path)
    yield tmp_path
    # Restore original settings
    settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"] = original_dir


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
