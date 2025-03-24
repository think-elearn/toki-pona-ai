"""
Service for managing Sitelen Pona template images.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import cv2
import numpy as np
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TemplateManagementService:
    """
    Service for managing Sitelen Pona template images.

    This service handles loading template images from S3 or local storage
    and preprocessing them for character recognition.
    """

    # Cache keys
    TEMPLATE_LIST_CACHE_KEY = "sitelen_pona_template_list"
    TEMPLATE_CACHE_PREFIX = "sitelen_pona_template_"

    def __init__(self):
        """Initialize the template management service."""
        self.use_s3 = settings.ML_MODELS_STORAGE["USE_S3"]
        self.s3_bucket = settings.ML_MODELS_STORAGE["S3_MODELS_BUCKET_NAME"]
        self.s3_prefix = "templates/"  # S3 prefix for template images

        # Local templates directory
        if not self.use_s3:
            self.templates_dir = os.path.join(settings.MEDIA_ROOT, "templates")
            os.makedirs(self.templates_dir, exist_ok=True)

    def get_template_list(self) -> List[str]:
        """
        Get a list of available template names.

        Returns:
            List[str]: List of template names (without extension)
        """
        # Check cache first
        cached_list = cache.get(self.TEMPLATE_LIST_CACHE_KEY)
        if cached_list:
            return cached_list

        template_list = []

        if self.use_s3:
            # List templates in S3
            s3_client = boto3.client("s3")
            try:
                response = s3_client.list_objects_v2(
                    Bucket=self.s3_bucket, Prefix=self.s3_prefix
                )

                if "Contents" in response:
                    for item in response["Contents"]:
                        key = item["Key"]
                        if key.endswith(".png"):
                            # Extract the template name without extension
                            name = Path(key).stem
                            template_list.append(name)
            except Exception as e:
                logger.error(f"Error listing templates from S3: {str(e)}")
        else:
            # List templates in local directory
            try:
                for file in os.listdir(self.templates_dir):
                    if file.endswith(".png"):
                        name = Path(file).stem
                        template_list.append(name)
            except Exception as e:
                logger.error(f"Error listing local templates: {str(e)}")

        # Sort the list
        template_list.sort()

        # Cache the list
        cache.set(self.TEMPLATE_LIST_CACHE_KEY, template_list, timeout=3600)  # 1 hour

        return template_list

    def get_template_image(self, template_name: str) -> Optional[np.ndarray]:
        """
        Get a template image by name.

        Args:
            template_name: Name of the template (without extension)

        Returns:
            Optional[np.ndarray]: Template image as numpy array, or None if not found
        """
        # Check cache first
        cache_key = f"{self.TEMPLATE_CACHE_PREFIX}{template_name}"
        cached_image_bytes = cache.get(cache_key)

        if cached_image_bytes:
            # Convert bytes to numpy array
            image = np.frombuffer(cached_image_bytes, dtype=np.uint8)
            return cv2.imdecode(image, cv2.IMREAD_COLOR)

        image = None

        if self.use_s3:
            # Get template from S3
            s3_client = boto3.client("s3")
            s3_key = f"{self.s3_prefix}{template_name}.png"

            try:
                with tempfile.NamedTemporaryFile() as tmp_file:
                    s3_client.download_file(self.s3_bucket, s3_key, tmp_file.name)
                    image = cv2.imread(tmp_file.name)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    logger.warning(f"Template not found in S3: {template_name}")
                else:
                    logger.error(f"Error downloading template from S3: {str(e)}")
        else:
            # Get template from local directory
            local_path = os.path.join(self.templates_dir, f"{template_name}.png")
            if os.path.exists(local_path):
                image = cv2.imread(local_path)
            else:
                logger.warning(f"Template not found locally: {template_name}")

        # Cache the image if found
        if image is not None:
            # Encode image to bytes for caching
            _, image_bytes = cv2.imencode(".png", image)
            cache.set(cache_key, image_bytes.tobytes(), timeout=3600)  # 1 hour

        return image

    def preprocess_template(self, template_image: np.ndarray) -> np.ndarray:
        """
        Preprocess a template image for feature extraction.

        Args:
            template_image: Original template image

        Returns:
            np.ndarray: Preprocessed image ready for feature extraction
        """
        # Convert to grayscale if needed
        if len(template_image.shape) == 3 and template_image.shape[2] == 3:
            gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = template_image

        # Threshold to create binary image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # Ensure the image is 8-bit for feature extraction
        if binary.dtype != np.uint8:
            binary = binary.astype(np.uint8)

        return binary

    def load_all_templates(self) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Load and preprocess all template images.

        Returns:
            Dict[str, Dict[str, np.ndarray]]: Dictionary mapping template names to
                                             dictionaries with 'original' and 'processed' images
        """
        templates = {}
        template_list = self.get_template_list()

        for template_name in template_list:
            original = self.get_template_image(template_name)
            if original is not None:
                processed = self.preprocess_template(original)
                templates[template_name] = {
                    "original": original,
                    "processed": processed,
                }

        logger.info(f"Loaded {len(templates)} template images")
        return templates

    def upload_template(self, template_name: str, image_data: bytes) -> bool:
        """
        Upload a new template image.

        Args:
            template_name: Name for the template (without extension)
            image_data: Binary image data

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Invalid cache
            cache.delete(self.TEMPLATE_LIST_CACHE_KEY)
            cache.delete(f"{self.TEMPLATE_CACHE_PREFIX}{template_name}")

            if self.use_s3:
                # Upload to S3
                s3_client = boto3.client("s3")
                s3_key = f"{self.s3_prefix}{template_name}.png"

                with tempfile.NamedTemporaryFile() as tmp_file:
                    tmp_file.write(image_data)
                    tmp_file.flush()

                    s3_client.upload_file(
                        tmp_file.name,
                        self.s3_bucket,
                        s3_key,
                        ExtraArgs={"ACL": "public-read", "ContentType": "image/png"},
                    )
            else:
                # Save locally
                local_path = os.path.join(self.templates_dir, f"{template_name}.png")
                with open(local_path, "wb") as f:
                    f.write(image_data)

            logger.info(f"Uploaded template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error uploading template: {str(e)}")
            return False

    def delete_template(self, template_name: str) -> bool:
        """
        Delete a template image.

        Args:
            template_name: Name of the template to delete (without extension)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Invalid cache
            cache.delete(self.TEMPLATE_LIST_CACHE_KEY)
            cache.delete(f"{self.TEMPLATE_CACHE_PREFIX}{template_name}")

            if self.use_s3:
                # Delete from S3
                s3_client = boto3.client("s3")
                s3_key = f"{self.s3_prefix}{template_name}.png"

                s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
            else:
                # Delete locally
                local_path = os.path.join(self.templates_dir, f"{template_name}.png")
                if os.path.exists(local_path):
                    os.remove(local_path)

            logger.info(f"Deleted template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting template: {str(e)}")
            return False


# Create a singleton instance
template_service = TemplateManagementService()
