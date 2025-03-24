"""
Service for managing Sitelen Pona SVG files.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SVGManagementService:
    """
    Service for managing Sitelen Pona SVG files.

    This service handles loading SVG files from S3 or local storage.
    """

    # Cache keys
    SVG_LIST_CACHE_KEY = "sitelen_pona_svg_list"
    SVG_CACHE_PREFIX = "sitelen_pona_svg_"

    def __init__(self):
        """Initialize the SVG management service."""
        self.use_s3 = settings.ML_MODELS_STORAGE["USE_S3"]
        self.s3_bucket = settings.ML_MODELS_STORAGE["S3_MODELS_BUCKET_NAME"]
        self.s3_prefix = "sitelen_pona_svgs/"  # S3 prefix for SVG files

        # Local SVG directory
        if not self.use_s3:
            self.svg_dir = os.path.join(settings.MEDIA_ROOT, "sitelen_pona_svgs")
            os.makedirs(self.svg_dir, exist_ok=True)

    def get_svg_list(self) -> List[str]:
        """
        Get a list of available SVG names.

        Returns:
            List[str]: List of SVG names (without extension)
        """
        # Check cache first
        cached_list = cache.get(self.SVG_LIST_CACHE_KEY)
        if cached_list:
            return cached_list

        svg_list = []

        if self.use_s3:
            # List SVGs in S3
            s3_client = boto3.client("s3")
            try:
                response = s3_client.list_objects_v2(
                    Bucket=self.s3_bucket, Prefix=self.s3_prefix
                )

                if "Contents" in response:
                    for item in response["Contents"]:
                        key = item["Key"]
                        if key.endswith(".svg"):
                            # Extract the SVG name without extension
                            name = Path(key).stem
                            svg_list.append(name)
            except Exception as e:
                logger.error(f"Error listing SVGs from S3: {str(e)}")
        else:
            # List SVGs in local directory
            try:
                for file in os.listdir(self.svg_dir):
                    if file.endswith(".svg"):
                        name = Path(file).stem
                        svg_list.append(name)
            except Exception as e:
                logger.error(f"Error listing local SVGs: {str(e)}")

        # Sort the list
        svg_list.sort()

        # Cache the list
        cache.set(self.SVG_LIST_CACHE_KEY, svg_list, timeout=3600)  # 1 hour

        return svg_list

    def get_svg_content(self, svg_name: str) -> Optional[str]:
        """
        Get SVG content by name.

        Args:
            svg_name: Name of the SVG (without extension)

        Returns:
            Optional[str]: SVG content as string, or None if not found
        """
        # Check cache first
        cache_key = f"{self.SVG_CACHE_PREFIX}{svg_name}"
        cached_content = cache.get(cache_key)

        if cached_content:
            return cached_content

        content = None

        if self.use_s3:
            # Get SVG from S3
            s3_client = boto3.client("s3")
            s3_key = f"{self.s3_prefix}{svg_name}.svg"

            try:
                response = s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
                content = response["Body"].read().decode("utf-8")
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(f"SVG not found in S3: {svg_name}")
                else:
                    logger.error(f"Error downloading SVG from S3: {str(e)}")
        else:
            # Get SVG from local directory
            local_path = os.path.join(self.svg_dir, f"{svg_name}.svg")
            if os.path.exists(local_path):
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                logger.warning(f"SVG not found locally: {svg_name}")

        # Cache the content if found
        if content is not None:
            cache.set(cache_key, content, timeout=3600)  # 1 hour

        return content

    def get_svg_url(self, svg_name: str) -> Optional[str]:
        """
        Get the URL for an SVG file.

        Args:
            svg_name: Name of the SVG (without extension)

        Returns:
            Optional[str]: URL to the SVG file, or None if not available
        """
        if self.use_s3:
            # Construct S3 URL using the endpoint from settings
            return f"{settings.AWS_S3_ENDPOINT_URL}/{self.s3_bucket}/{self.s3_prefix}{svg_name}.svg"
        else:
            # Construct local URL
            return f"{settings.MEDIA_URL}sitelen_pona_svgs/{svg_name}.svg"

    def upload_svg(self, svg_name: str, svg_content: str) -> bool:
        """
        Upload a new SVG file.

        Args:
            svg_name: Name for the SVG (without extension)
            svg_content: SVG content as string

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Invalidate cache
            cache.delete(self.SVG_LIST_CACHE_KEY)
            cache.delete(f"{self.SVG_CACHE_PREFIX}{svg_name}")

            if self.use_s3:
                # Upload to S3
                s3_client = boto3.client("s3")
                s3_key = f"{self.s3_prefix}{svg_name}.svg"

                s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=svg_content.encode("utf-8"),
                    ContentType="image/svg+xml",
                    ACL="public-read",
                )
            else:
                # Save locally
                local_path = os.path.join(self.svg_dir, f"{svg_name}.svg")
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(svg_content)

            logger.info(f"Uploaded SVG: {svg_name}")
            return True
        except Exception as e:
            logger.error(f"Error uploading SVG: {str(e)}")
            return False

    def delete_svg(self, svg_name: str) -> bool:
        """
        Delete an SVG file.

        Args:
            svg_name: Name of the SVG to delete (without extension)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Invalidate cache
            cache.delete(self.SVG_LIST_CACHE_KEY)
            cache.delete(f"{self.SVG_CACHE_PREFIX}{svg_name}")

            if self.use_s3:
                # Delete from S3
                s3_client = boto3.client("s3")
                s3_key = f"{self.s3_prefix}{svg_name}.svg"

                s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
            else:
                # Delete locally
                local_path = os.path.join(self.svg_dir, f"{svg_name}.svg")
                if os.path.exists(local_path):
                    os.remove(local_path)

            logger.info(f"Deleted SVG: {svg_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting SVG: {str(e)}")
            return False


# Create a singleton instance
svg_service = SVGManagementService()
