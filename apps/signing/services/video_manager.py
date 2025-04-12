"""
Service for managing sign language videos across development and production environments.
This utility helps keep videos out of Git while ensuring they're available when needed.
"""

import logging
import os
import shutil
import tempfile

import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class VideoManager:
    """
    Service to manage sign language videos across environments.
    Handles local and S3 storage with fallback mechanisms.
    """

    def __init__(self):
        """Initialize the video manager with configuration."""
        # Determine if we're using S3 in this environment
        self.use_s3 = getattr(settings, "USE_S3_STORAGE", False)

        # Local static directories
        self.static_video_dir = os.path.join(
            settings.STATICFILES_DIRS[0], "videos", "lukapona", "mp4"
        )

        # Create directories if they don't exist
        os.makedirs(self.static_video_dir, exist_ok=True)

        # S3 configuration
        if self.use_s3:
            self.s3_bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
            self.s3_region = getattr(settings, "AWS_S3_REGION_NAME", None)
            self.s3_endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
            self.s3_video_prefix = "videos/lukapona/mp4/"

            # Initialize S3 client
            self.s3_client = boto3.client(
                "s3",
                region_name=self.s3_region,
                endpoint_url=self.s3_endpoint_url,
                aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            )

    def get_local_video_path(self, sign_name):
        """
        Get the local path for a sign video.

        Args:
            sign_name: Name of the sign

        Returns:
            Path to the local video file
        """
        video_filename = f"{sign_name}.mp4"
        return os.path.join(self.static_video_dir, video_filename)

    def get_s3_video_key(self, sign_name):
        """
        Get the S3 key for a sign video.

        Args:
            sign_name: Name of the sign

        Returns:
            S3 key for the video
        """
        video_filename = f"{sign_name}.mp4"
        return f"{self.s3_video_prefix}{video_filename}"

    def video_exists_locally(self, sign_name):
        """
        Check if a video exists locally.

        Args:
            sign_name: Name of the sign

        Returns:
            True if the video exists locally, False otherwise
        """
        local_path = self.get_local_video_path(sign_name)
        return os.path.exists(local_path)

    def video_exists_in_s3(self, sign_name):
        """
        Check if a video exists in S3.

        Args:
            sign_name: Name of the sign

        Returns:
            True if the video exists in S3, False otherwise
        """
        if not self.use_s3:
            return False

        try:
            s3_key = self.get_s3_video_key(sign_name)
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            return True
        except ClientError:
            return False

    def download_from_s3(self, sign_name, force=False):
        """
        Download a video from S3 to local storage.

        Args:
            sign_name: Name of the sign
            force: If True, download even if file exists locally

        Returns:
            Path to the downloaded file or None if failed
        """
        if not self.use_s3:
            logger.warning("S3 storage not configured, cannot download")
            return None

        local_path = self.get_local_video_path(sign_name)

        # Skip if already exists locally and not forcing
        if not force and os.path.exists(local_path):
            logger.debug(f"Video for {sign_name} already exists locally")
            return local_path

        try:
            s3_key = self.get_s3_video_key(sign_name)
            logger.info(f"Downloading {sign_name} video from S3: {s3_key}")

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                self.s3_client.download_fileobj(
                    Bucket=self.s3_bucket, Key=s3_key, Fileobj=tmp
                )
                tmp_path = tmp.name

            # Move to final destination
            shutil.move(tmp_path, local_path)
            logger.info(f"Downloaded {sign_name} video to {local_path}")
            return local_path
        except Exception as e:
            logger.exception(f"Error downloading {sign_name} video from S3: {e}")
            return None

    def upload_to_s3(self, sign_name):
        """
        Upload a video from local storage to S3.

        Args:
            sign_name: Name of the sign

        Returns:
            S3 URL of the uploaded file or None if failed
        """
        if not self.use_s3:
            logger.warning("S3 storage not configured, cannot upload")
            return None

        local_path = self.get_local_video_path(sign_name)

        if not os.path.exists(local_path):
            logger.error(f"Video for {sign_name} does not exist locally")
            return None

        try:
            s3_key = self.get_s3_video_key(sign_name)
            logger.info(f"Uploading {sign_name} video to S3: {s3_key}")

            self.s3_client.upload_file(
                Filename=local_path, Bucket=self.s3_bucket, Key=s3_key
            )

            # Construct the S3 URL
            if self.s3_endpoint_url:
                # For custom endpoints like Tigris
                s3_url = f"{self.s3_endpoint_url}/{self.s3_bucket}/{s3_key}"
            else:
                # For standard AWS S3
                s3_url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{s3_key}"

            logger.info(f"Uploaded {sign_name} video to {s3_url}")
            return s3_url
        except Exception as e:
            logger.exception(f"Error uploading {sign_name} video to S3: {e}")
            return None

    def download_from_url(self, sign_name, url):
        """
        Download a video from a URL to local storage.

        Args:
            sign_name: Name of the sign
            url: URL to download from

        Returns:
            Path to the downloaded file or None if failed
        """
        local_path = self.get_local_video_path(sign_name)

        try:
            logger.info(f"Downloading {sign_name} video from URL: {url}")

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                response = requests.get(url, stream=True)
                response.raise_for_status()

                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                tmp_path = tmp.name

            # Move to final destination
            shutil.move(tmp_path, local_path)
            logger.info(f"Downloaded {sign_name} video to {local_path}")
            return local_path
        except Exception as e:
            logger.exception(f"Error downloading {sign_name} video from URL: {e}")
            return None

    def get_video_path(self, sign_name):
        """
        Get the path to a sign video, downloading it if necessary.

        Args:
            sign_name: Name of the sign

        Returns:
            Path to the video file or None if not available
        """
        # First check if it exists locally
        local_path = self.get_local_video_path(sign_name)
        if os.path.exists(local_path):
            return local_path

        # If not, try to download from S3
        if self.use_s3 and self.video_exists_in_s3(sign_name):
            downloaded_path = self.download_from_s3(sign_name)
            if downloaded_path:
                return downloaded_path

        logger.warning(f"Video for {sign_name} not found locally or in S3")
        return None

    def _get_local_videos(self):
        """
        Get dictionary of locally available videos.

        Returns:
            Dictionary mapping sign names to local video paths
        """
        videos = {}
        try:
            if os.path.exists(self.static_video_dir):
                for filename in os.listdir(self.static_video_dir):
                    if filename.endswith(".mp4"):
                        # Extract sign name from filename (remove extension)
                        sign_name = os.path.splitext(filename)[0]
                        videos[sign_name] = os.path.join(
                            self.static_video_dir, filename
                        )
        except Exception as e:
            logger.exception(f"Error scanning local video directory: {e}")

        return videos

    def _get_s3_videos(self):
        """
        Get dictionary of videos available in S3.

        Returns:
            Dictionary mapping sign names to S3 keys
        """
        videos = {}
        if not self.use_s3:
            return videos

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket, Prefix=self.s3_video_prefix
            )

            if "Contents" in response:
                for item in response["Contents"]:
                    key = item["Key"]
                    if key.endswith(".mp4"):
                        filename = os.path.basename(key)
                        sign_name = os.path.splitext(filename)[0]
                        videos[sign_name] = key
        except Exception as e:
            logger.exception(f"Error listing videos in S3: {e}")

        return videos

    def list_available_videos(self):
        """
        List all available sign videos.

        Returns:
            Dictionary mapping sign names to video paths
        """
        # Get locally available videos
        videos = self._get_local_videos()

        # Add S3 videos that aren't available locally
        s3_videos = self._get_s3_videos()
        for sign_name, key in s3_videos.items():
            if sign_name not in videos:
                videos[sign_name] = key

        return videos
