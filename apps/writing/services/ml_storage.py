"""
Service for managing ML model storage and retrieval.
"""

import hashlib
import logging
import os
import tempfile
import time
import urllib.request

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ModelStorageService:
    """
    Service for managing ML model storage and retrieval.

    This service handles downloading, caching, and retrieving ML models
    from either local storage or S3 depending on configuration.
    """

    # Cache keys for models
    MOBILENET_CACHE_KEY = "mobilenet_model_path"

    def __init__(self):
        """Initialize the model storage service."""
        self.use_s3 = settings.ML_MODELS_STORAGE["USE_S3"]

        # Always prefer the development setting (MEDIA_ROOT) for local storage
        if hasattr(settings, "MEDIA_ROOT"):
            self.local_models_dir = os.path.join(settings.MEDIA_ROOT, "ml_models")
        else:
            # Fallback to the setting in base.py
            self.local_models_dir = settings.ML_MODELS_STORAGE["LOCAL_MODELS_DIR"]

        self.s3_bucket = settings.ML_MODELS_STORAGE["S3_MODELS_BUCKET_NAME"]
        self.s3_prefix = settings.ML_MODELS_STORAGE["S3_MODELS_KEY_PREFIX"]
        self.mobilenet_path = settings.ML_MODELS_STORAGE["MOBILENET_MODEL_PATH"]
        self.mobilenet_url = settings.ML_MODELS_STORAGE["MOBILENET_MODEL_URL"]

        # Ensure local models directory exists if using local storage
        if not self.use_s3:
            logger.info(f"Creating models directory at {self.local_models_dir}")
            os.makedirs(self.local_models_dir, exist_ok=True)

    def get_mobilenet_model_path(self):
        """
        Get the path to the MobileNet model.

        If the model doesn't exist, it will be downloaded.
        For S3 storage, the model will be downloaded to a temporary file.

        Returns:
            str: Path to the MobileNet model file
        """
        # Check cache first
        cached_path = cache.get(self.MOBILENET_CACHE_KEY)
        if cached_path and os.path.exists(cached_path):
            logger.info(f"Using cached MobileNet model at {cached_path}")
            return cached_path

        if self.use_s3:
            return self._get_mobilenet_from_s3()
        else:
            return self._get_mobilenet_local()

    def _get_mobilenet_local(self):
        """Get the MobileNet model from local storage."""
        local_path = os.path.join(self.local_models_dir, self.mobilenet_path)

        # Download if it doesn't exist
        if not os.path.exists(local_path):
            logger.info(f"Downloading MobileNet model to {local_path}")
            self._download_model(self.mobilenet_url, local_path)

        # Cache the path
        cache.set(self.MOBILENET_CACHE_KEY, local_path, timeout=3600)  # 1 hour
        return local_path

    def _get_mobilenet_from_s3(self):
        """
        Get the MobileNet model from S3.

        The model is downloaded to a temporary file if it's not already cached.
        """
        s3_key = f"{self.s3_prefix}{self.mobilenet_path}"

        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        local_path = os.path.join(temp_dir, f"{self.mobilenet_path}")

        # Check if we already have the file cached
        if os.path.exists(local_path):
            # Cache hit - use the temporary file
            cache.set(self.MOBILENET_CACHE_KEY, local_path, timeout=3600)  # 1 hour
            return local_path

        # Check if the model exists in S3
        s3_client = boto3.client("s3")
        try:
            s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            logger.info(f"Found MobileNet model in S3 at {s3_key}")

            # Download from S3 to temporary file
            s3_client.download_file(self.s3_bucket, s3_key, local_path)
            logger.info(f"Downloaded MobileNet model from S3 to {local_path}")

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # Model doesn't exist in S3, download from source
                logger.info("MobileNet model not found in S3, downloading from source")
                self._download_model(self.mobilenet_url, local_path)

                # Upload to S3 for future use
                self._upload_to_s3(local_path, s3_key)
            else:
                # Some other error, re-raise
                raise

        # Cache the path
        cache.set(self.MOBILENET_CACHE_KEY, local_path, timeout=3600)  # 1 hour
        return local_path

    def _download_model(self, url, path):
        """Download a model from a URL to a local path."""
        try:
            logger.info(f"Downloading model from {url} to {path}")
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Download with progress tracking
            start_time = time.time()
            urllib.request.urlretrieve(url, path)
            elapsed = time.time() - start_time

            # Log download stats
            size_mb = os.path.getsize(path) / (1024 * 1024)
            logger.info(f"Downloaded {size_mb:.2f} MB in {elapsed:.2f} seconds")

            return path
        except Exception as e:
            logger.error(f"Error downloading model: {str(e)}")
            # Clean up partial download if it exists
            if os.path.exists(path):
                os.remove(path)
            raise

    def _upload_to_s3(self, local_path, s3_key):
        """Upload a local file to S3."""
        try:
            logger.info(f"Uploading {local_path} to S3 at {s3_key}")
            s3_client = boto3.client("s3")
            s3_client.upload_file(
                local_path, self.s3_bucket, s3_key, ExtraArgs={"ACL": "public-read"}
            )
            logger.info("Upload complete")
            return True
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return False

    def get_model_hash(self, model_path):
        """Calculate the MD5 hash of a model file."""
        hash_md5 = hashlib.md5()
        with open(model_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


# Create a singleton instance
model_storage = ModelStorageService()
